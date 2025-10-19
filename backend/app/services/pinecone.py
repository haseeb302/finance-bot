from pinecone import Pinecone
from typing import List, Dict, Any, Optional
from app.core.settings import settings
import asyncio
import uuid


class PineconeService:
    def __init__(self):
        """Initialize Pinecone service with existing index."""
        try:
            self.pc = Pinecone(api_key=settings.pinecone_api_key)
            self.index_name = settings.pinecone_index_name
            # Connect to existing index
            self.index = self.pc.Index(self.index_name)
        except Exception as e:
            raise Exception(f"Failed to connect to Pinecone index: {str(e)}")

    async def upsert_vectors(
        self, vectors: List[Dict[str, Any]], namespace: str = "default"
    ) -> Dict[str, Any]:
        """Upsert vectors to Pinecone index."""
        try:
            response = self.index.upsert(vectors=vectors, namespace=namespace)
            return response
        except Exception as e:
            raise Exception(f"Failed to upsert vectors: {str(e)}")

    async def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        namespace: str = "default",
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """Query vectors from Pinecone index."""
        try:
            response = self.index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                include_metadata=include_metadata,
            )
            return response
        except Exception as e:
            raise Exception(f"Failed to query vectors: {str(e)}")

    async def delete_vectors(
        self, ids: List[str], namespace: str = "default"
    ) -> Dict[str, Any]:
        """Delete vectors from Pinecone index."""
        try:
            response = self.index.delete(ids=ids, namespace=namespace)
            return response
        except Exception as e:
            raise Exception(f"Failed to delete vectors: {str(e)}")

    async def search_similar_documents(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        try:
            response = await self.query_vectors(
                query_vector=query_vector, top_k=top_k, include_metadata=True
            )

            results = []
            for match in response.matches:
                result = {
                    "id": match.id,
                    "score": match.score,
                    "similarity": match.score,
                    "metadata": match.metadata or {},
                }
                results.append(result)

            return results
        except Exception as e:
            raise Exception(f"Failed to search similar documents: {str(e)}")

    async def add_document(
        self,
        document_id: str,
        vector: List[float],
        metadata: Dict[str, Any],
        namespace: str = "default",
    ) -> Dict[str, Any]:
        """Add a single document to Pinecone."""
        try:
            vector_data = {"id": document_id, "values": vector, "metadata": metadata}

            response = await self.upsert_vectors([vector_data], namespace)
            return response
        except Exception as e:
            raise Exception(f"Failed to add document: {str(e)}")

    async def update_document(
        self,
        document_id: str,
        vector: List[float],
        metadata: Dict[str, Any],
        namespace: str = "default",
    ) -> Dict[str, Any]:
        """Update a document in Pinecone."""
        return await self.add_document(document_id, vector, metadata, namespace)

    async def delete_document(
        self, document_id: str, namespace: str = "default"
    ) -> Dict[str, Any]:
        """Delete a document from Pinecone."""
        try:
            response = await self.delete_vectors([document_id], namespace)
            return response
        except Exception as e:
            raise Exception(f"Failed to delete document: {str(e)}")

    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        try:
            return self.index.describe_index_stats()
        except Exception as e:
            raise Exception(f"Failed to get index stats: {str(e)}")


# Global instance
pinecone_service = PineconeService()
