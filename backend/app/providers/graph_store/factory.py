from app.core.config import settings
from app.core.logging import logger
from app.providers.graph_store.base import GraphStore
from app.providers.graph_store.in_memory_store import InMemoryGraphStore
from app.providers.graph_store.neo4j_store import Neo4jGraphStore

_in_memory_graph_store_instance = InMemoryGraphStore()
_neo4j_store_instance = None


def get_graph_store() -> GraphStore:
    """Factory to retrieve configured GraphStore (Neo4j or In-Memory)."""
    global _neo4j_store_instance

    if settings.GRAPH_STORE_PROVIDER == "neo4j":
        try:
            if _neo4j_store_instance is None:
                _neo4j_store_instance = Neo4jGraphStore()
            return _neo4j_store_instance
        except Exception as e:
            logger.warning(
                f"Failed to connect to Neo4j graph store ({e}). Falling back to InMemoryGraphStore."
            )
            return _in_memory_graph_store_instance

    return _in_memory_graph_store_instance
