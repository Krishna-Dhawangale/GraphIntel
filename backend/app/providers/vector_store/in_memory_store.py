import math
from typing import Dict, List, Optional

from app.providers.vector_store.base import VectorRecord, VectorSearchResult, VectorStore


class InMemoryVectorStore(VectorStore):
    """In-memory cosine similarity vector store for tests, CI, and local dev."""

    def __init__(self):
        self._records: Dict[str, VectorRecord] = {}

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def create_collection(self, dimension: int) -> bool:
        return True

    async def upsert(self, records: List[VectorRecord]) -> bool:
        for r in records:
            self._records[r.id] = r
        return True

    async def search(
        self,
        query_vector: List[float],
        top_k: int,
        filter_user_id: str,
        filter_document_ids: Optional[List[str]] = None,
    ) -> List[VectorSearchResult]:
        matches: List[VectorSearchResult] = []

        for record in self._records.values():
            # Check user ownership
            if record.payload.get("user_id") != filter_user_id:
                continue
            # Check document filter
            if filter_document_ids and record.payload.get("document_id") not in filter_document_ids:
                continue

            score = self._cosine_similarity(query_vector, record.vector)
            matches.append(VectorSearchResult(id=record.id, score=score, payload=record.payload))

        # Sort descending by score
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:top_k]

    async def delete(self, ids: List[str]) -> bool:
        for doc_id in ids:
            self._records.pop(doc_id, None)
        return True

    async def delete_by_document(self, document_id: str, user_id: str) -> bool:
        to_delete = [
            r_id
            for r_id, r in self._records.items()
            if r.payload.get("document_id") == document_id and r.payload.get("user_id") == user_id
        ]
        for r_id in to_delete:
            self._records.pop(r_id, None)
        return True

    async def health_check(self) -> bool:
        return True
