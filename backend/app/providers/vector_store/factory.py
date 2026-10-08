from app.core.config import settings
from app.providers.vector_store.base import VectorStore
from app.providers.vector_store.in_memory_store import InMemoryVectorStore
from app.providers.vector_store.qdrant_store import QdrantVectorStore

# In-memory singleton instance for dev/test persistence across calls in same process
_in_memory_store_instance = InMemoryVectorStore()


def get_vector_store() -> VectorStore:
    """Factory to retrieve configured VectorStore (Qdrant or In-Memory)."""
    if settings.VECTOR_STORE_PROVIDER == "qdrant":
        try:
            return QdrantVectorStore()
        except Exception:
            return _in_memory_store_instance
    return _in_memory_store_instance
