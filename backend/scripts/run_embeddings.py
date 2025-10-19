#!/usr/bin/env python3
"""
Script to chunk content files and populate Pinecone with embeddings using hosted llama-text-embed-v2
"""

import asyncio
import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.pinecone import pinecone_service
from app.core.settings import settings
import structlog

logger = structlog.get_logger(__name__)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks for better context preservation.

    Args:
        text: Input text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 100 characters
            sentence_end = text.rfind(".", start, end)
            if sentence_end > start + chunk_size // 2:
                end = sentence_end + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break

    return chunks


async def get_llama_embedding(text: str) -> List[float]:
    """
    Get embedding using Pinecone's hosted llama-text-embed-v2 model via REST API.

    Args:
        text: Text to embed

    Returns:
        Embedding vector (1024 dimensions)
    """
    try:
        import httpx

        # Validate API key
        if not settings.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is not set in environment variables")

        # Pinecone Inference API endpoint
        api_url = "https://api.pinecone.io/embed"
        headers = {
            "Api-Key": settings.pinecone_api_key,
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": "2025-10",
        }
        payload = {
            "model": "llama-text-embed-v2",
            "parameters": {"input_type": "passage", "truncate": "END"},
            "inputs": [{"text": text}],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()

            if "data" not in result or not result["data"]:
                raise ValueError("No embedding data received from Pinecone")

            embedding = result["data"][0]["values"]

            if len(embedding) != 1024:
                raise ValueError(
                    f"Invalid embedding dimension: {len(embedding)}, expected 1024"
                )

            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

    except Exception as e:
        logger.error(f"Failed to generate embedding: {str(e)}")
        raise


async def process_content_files() -> bool:
    """
    Process all content files and populate Pinecone with embeddings.

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Starting content processing and embedding creation...")

        # Check if index already has data
        stats = pinecone_service.get_index_stats()
        total_vectors = stats.get("total_vector_count", 0)
        logger.info(f"Current index has {total_vectors} vectors")

        if total_vectors > 0:
            logger.warning("Index already contains data. This will add new vectors.")
            response = input("Do you want to continue? (y/N): ")
            if response.lower() != "y":
                logger.info("Aborted by user.")
                return False

        # Get all .txt files from content directory
        content_dir = backend_dir / "content"
        if not content_dir.exists():
            logger.error(f"Content directory not found: {content_dir}")
            return False

        txt_files = list(content_dir.glob("*.txt"))
        if not txt_files:
            logger.error("No .txt files found in content directory")
            return False

        logger.info(f"Found {len(txt_files)} content files")

        total_chunks = 0
        vectors_to_upsert = []

        # Process each file
        for file_path in txt_files:
            category = file_path.stem  # filename without extension
            logger.info(f"Processing file: {file_path.name} (category: {category})")

            try:
                # Read file content
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                if not content:
                    logger.warning(f"Empty file: {file_path.name}")
                    continue

                # Chunk the content
                chunks = chunk_text(content, chunk_size=800, overlap=100)
                logger.info(f"Created {len(chunks)} chunks for {file_path.name}")

                # Process each chunk
                for i, chunk in enumerate(chunks):
                    try:
                        # Generate embedding using Pinecone's hosted model
                        embedding = await get_llama_embedding(chunk)

                        # Create vector data
                        vector_id = f"{category}_{i}_{hash(chunk) % 10000}"
                        vector_data = {
                            "id": vector_id,
                            "values": embedding,
                            "metadata": {
                                "category": category,
                                "source_file": file_path.name,
                                "chunk_index": i,
                                "text": chunk[:500],  # First 500 chars for reference
                                "vector_type": "dense",
                            },
                        }

                        vectors_to_upsert.append(vector_data)
                        total_chunks += 1

                        # Upsert in batches to avoid memory issues
                        if len(vectors_to_upsert) >= 50:
                            await pinecone_service.upsert_vectors(vectors_to_upsert)
                            logger.info(
                                f"Upserted batch of {len(vectors_to_upsert)} vectors"
                            )
                            vectors_to_upsert = []

                    except Exception as e:
                        logger.error(
                            f"Error processing chunk {i} from {file_path.name}: {str(e)}"
                        )
                        continue

            except Exception as e:
                logger.error(f"Error processing file {file_path.name}: {str(e)}")
                continue

        # Upsert remaining vectors
        if vectors_to_upsert:
            await pinecone_service.upsert_vectors(vectors_to_upsert)
            logger.info(f"Upserted final batch of {len(vectors_to_upsert)} vectors")

        # Get final stats
        final_stats = pinecone_service.get_index_stats()
        final_vectors = final_stats.get("total_vector_count", 0)

        logger.info(f"✅ Successfully processed content files!")
        logger.info(f"Total chunks created: {total_chunks}")
        logger.info(f"Total vectors in index: {final_vectors}")
        logger.info(f"Index dimension: {final_stats.get('dimension', 0)}")

        return True

    except Exception as e:
        logger.error(f"Failed to process content files: {str(e)}")
        return False


async def test_search():
    """Test the search functionality with a sample query."""
    try:
        logger.info("Testing search functionality...")

        # Test query
        test_query = "How do I create an account?"

        # Generate embedding for test query
        query_embedding = await get_llama_embedding(test_query)

        # Search Pinecone
        results = await pinecone_service.search_similar_documents(
            query_vector=query_embedding, top_k=3
        )

        logger.info(f"Search results for '{test_query}':")
        for i, result in enumerate(results, 1):
            logger.info(f"{i}. Score: {result['score']:.3f}")
            if "metadata" in result:
                logger.info(
                    f"   Category: {result['metadata'].get('category', 'Unknown')}"
                )
                logger.info(
                    f"   Source: {result['metadata'].get('source_file', 'Unknown')}"
                )
                logger.info(f"   Text: {result['metadata'].get('text', '')[:100]}...")

        return True

    except Exception as e:
        logger.error(f"Search test failed: {str(e)}")
        return False


async def main():
    """Main function to run the content processing and embedding population."""
    logger.info("🚀 Starting Content Processing and Embedding Population")

    # Check if we have the required environment variables
    required_vars = ["PINECONE_API_KEY", "PINECONE_INDEX_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set these variables in your .env.local file")
        return False

    # Process content files
    success = await process_content_files()

    if success:
        # Test search functionality
        await test_search()
        logger.info("🎉 Content processing completed successfully!")
    else:
        logger.error("❌ Content processing failed!")

    return success


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv(backend_dir / ".env.local")

    # Run the main function
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
