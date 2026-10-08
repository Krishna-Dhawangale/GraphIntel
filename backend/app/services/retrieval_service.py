from typing import List, Optional

from app.core.config import settings
from app.core.logging import log_event
from app.providers.embeddings.factory import get_embedding_provider
from app.providers.vector_store.factory import get_vector_store
from app.schemas.query import RetrievedChunk


class RetrievalService:
    def __init__(self):
        self.embedding_provider = get_embedding_provider()
        self.vector_store = get_vector_store()

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = settings.TOP_K,
        filters: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        """Retrieve top_k chunks matching query semantic vector enforcing user isolation."""
        # 1. Embed query
        query_vector = await self.embedding_provider.get_embedding(query)

        # 2. Vector search in vector store
        search_results = await self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
            filter_user_id=user_id,
            filter_document_ids=filters,
        )

        log_event(
            "vector_search",
            f"Retrieved {len(search_results)} chunks for user {user_id}",
            user_id=user_id,
            query=query,
            top_k=top_k,
            results_count=len(search_results),
        )

        # 3. Format into RetrievedChunk schemas
        chunks: List[RetrievedChunk] = []
        for res in search_results:
            payload = res.payload
            chunks.append(
                RetrievedChunk(
                    chunk_id=payload.get("chunk_id", res.id),
                    document_id=payload.get("document_id", ""),
                    filename=payload.get("filename", "Unknown"),
                    text=payload.get("text", ""),
                    page_number=payload.get("page_number"),
                    section=payload.get("section"),
                    score=round(res.score, 4),
                )
            )

        return chunks
