from typing import List, Dict, Any, Optional
from decimal import Decimal
from app.services.openai import openai_service
from app.services.pinecone import pinecone_service
from app.core.settings import settings
import asyncio
import uuid
import os


async def get_pinecone_embedding(text: str) -> List[float]:
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

        # Pinecone Inference API endpoint (latest 2025-10 version)
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

            return embedding

    except Exception as e:
        raise Exception(f"Failed to generate Pinecone embedding: {str(e)}")


class RAGService:
    def __init__(self):
        self.openai_service = openai_service
        self.pinecone_service = pinecone_service
        self.default_top_k = settings.default_top_k
        self.similarity_threshold = settings.similarity_threshold

    async def generate_response_with_rag(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = None,
    ) -> Dict[str, Any]:
        """Generate response using RAG (Retrieval-Augmented Generation)."""
        try:
            # Set default top_k
            if top_k is None:
                top_k = self.default_top_k

            # Step 1: Generate embedding for the query using Pinecone
            query_embedding = await get_pinecone_embedding(query)

            # Step 2: Retrieve similar documents from Pinecone
            similar_docs = await self.pinecone_service.search_similar_documents(
                query_vector=query_embedding, top_k=top_k
            )

            # Step 3: Filter documents by similarity threshold
            relevant_docs = [
                doc
                for doc in similar_docs
                if doc.get("score", 0) >= self.similarity_threshold
            ]

            # Log similarity scores for debugging
            if similar_docs:
                scores = [doc.get("score", 0) for doc in similar_docs]
                print(
                    f"Similarity scores: {scores}, threshold: {self.similarity_threshold}, relevant: {len(relevant_docs)}"
                )

            # Step 4: Prepare context from retrieved documents
            context = self._prepare_context(relevant_docs)

            # Step 5: Prepare messages for OpenAI
            messages = self._prepare_messages(query, chat_history)

            # Step 6: Generate response with context
            response = await self.openai_service.generate_response(
                messages=messages, context=context
            )

            # Step 7: Prepare sources for response
            sources = self._prepare_sources(relevant_docs)

            return {
                "content": response["content"],
                "sources": sources,
                "tokens_used": response["tokens_used"],
                "model": response["model"],
                "context_docs": len(relevant_docs),
                "similarity_scores": [
                    Decimal(str(doc.get("score", 0))) for doc in relevant_docs
                ],
            }

        except Exception as e:
            raise Exception(f"RAG generation failed: {str(e)}")

    def _prepare_context(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare context from retrieved documents."""
        context = []
        for doc in documents:
            metadata = doc.get("metadata", {})
            context.append(
                {
                    "title": metadata.get("source_file", "Unknown"),
                    "content": metadata.get("text", ""),
                    "source": metadata.get("source_file", ""),
                    "category": metadata.get("category", ""),
                    "similarity": doc.get("score", 0),
                }
            )
        return context

    def _prepare_messages(
        self, query: str, chat_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """Prepare messages for OpenAI."""
        messages = []

        # Add chat history if provided
        if chat_history:
            messages.extend(chat_history)

        # Add current query
        messages.append({"role": "user", "content": query})

        return messages

    def _prepare_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare sources for response."""
        sources = []
        for doc in documents:
            metadata = doc.get("metadata", {})
            source = {
                "title": metadata.get("source_file", "Unknown"),
                "source": metadata.get("source_file", ""),
                "category": metadata.get("category", ""),
                "similarity": Decimal(str(doc.get("score", 0))),
            }
            sources.append(source)
        return sources

    async def add_document_to_knowledge_base(
        self,
        title: str,
        content: str,
        source: Optional[str] = None,
        category: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a document to the knowledge base."""
        try:
            # Generate document ID if not provided
            if not document_id:
                document_id = str(uuid.uuid4())

            # Generate embedding for the content using Pinecone
            embedding = await get_pinecone_embedding(content)

            # Prepare metadata
            metadata = {
                "title": title,
                "content": content,
                "source": source or "",
                "category": category or "general",
            }

            # Add to Pinecone
            await self.pinecone_service.add_document(
                document_id=document_id, vector=embedding, metadata=metadata
            )

            return {"document_id": document_id, "title": title, "status": "success"}

        except Exception as e:
            raise Exception(f"Failed to add document to knowledge base: {str(e)}")

    async def update_document_in_knowledge_base(
        self,
        document_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        source: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a document in the knowledge base."""
        try:
            # Get existing document metadata
            # Note: In a real implementation, you'd fetch this from your database
            # For now, we'll assume the metadata is provided

            # Generate new embedding if content changed
            if content:
                embedding = await get_pinecone_embedding(content)
            else:
                # If content didn't change, we need to get the existing embedding
                # This would require querying the database for the original content
                raise Exception("Content must be provided for update")

            # Prepare updated metadata
            metadata = {
                "title": title or "Updated Document",
                "content": content or "",
                "source": source or "",
                "category": category or "general",
            }

            # Update in Pinecone
            await self.pinecone_service.update_document(
                document_id=document_id, vector=embedding, metadata=metadata
            )

            return {"document_id": document_id, "status": "success"}

        except Exception as e:
            raise Exception(f"Failed to update document in knowledge base: {str(e)}")

    async def delete_document_from_knowledge_base(
        self, document_id: str
    ) -> Dict[str, Any]:
        """Delete a document from the knowledge base."""
        try:
            await self.pinecone_service.delete_document(document_id)

            return {"document_id": document_id, "status": "success"}

        except Exception as e:
            raise Exception(f"Failed to delete document from knowledge base: {str(e)}")

    async def search_knowledge_base(
        self, query: str, top_k: int = 10, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base."""
        try:
            # Generate embedding for the query using Pinecone
            query_embedding = await get_pinecone_embedding(query)

            # Search Pinecone
            results = await self.pinecone_service.search_similar_documents(
                query_vector=query_embedding, top_k=top_k
            )

            # Filter by category if specified
            if category:
                results = [
                    doc
                    for doc in results
                    if doc.get("metadata", {}).get("category") == category
                ]

            return results

        except Exception as e:
            raise Exception(f"Failed to search knowledge base: {str(e)}")

    async def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        try:
            stats = self.pinecone_service.get_index_stats()
            return {
                "total_vectors": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", 0),
                "index_fullness": stats.get("index_fullness", 0),
            }
        except Exception as e:
            raise Exception(f"Failed to get knowledge base stats: {str(e)}")


# Global instance
rag_service = RAGService()
