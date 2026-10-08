from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class VectorRecord(BaseModel):
    id: str
    vector: List[float]
    payload: Dict[str, Any]


class VectorSearchResult(BaseModel):
    id: str
    score: float
    payload: Dict[str, Any]


class VectorStore(ABC):
    """Abstract interface for vector database operations."""

    @abstractmethod
    async def create_collection(self, dimension: int) -> bool:
        """Create the collection if it doesn't exist."""
        pass

    @abstractmethod
    async def upsert(self, records: List[VectorRecord]) -> bool:
        """Upsert a batch of vector records with metadata payloads."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int,
        filter_user_id: str,
        filter_document_ids: Optional[List[str]] = None,
    ) -> List[VectorSearchResult]:
        """Search nearest neighbor vectors enforcing user ownership and optional document filters."""
        pass

    @abstractmethod
    async def delete(self, ids: List[str]) -> bool:
        """Delete vectors by their IDs."""
        pass

    @abstractmethod
    async def delete_by_document(self, document_id: str, user_id: str) -> bool:
        """Delete all vectors belonging to a specific document and user."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify vector database connectivity and collection status."""
        pass
