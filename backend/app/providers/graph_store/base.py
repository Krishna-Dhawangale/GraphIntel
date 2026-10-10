from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.schemas.graph import (
    EntityCreate,
    EntityResponse,
    GraphVisualizationResponse,
    RelationshipCreate,
    RelationshipResponse,
)


class GraphStore(ABC):
    """Abstract interface for Knowledge Graph stores."""

    @abstractmethod
    async def initialize_schema(self) -> None:
        """Create required indexes, unique constraints, and schema safeguards."""
        pass

    @abstractmethod
    async def upsert_entity(self, user_id: str, entity: EntityCreate) -> EntityResponse:
        """Idempotently insert or update an entity node for a user."""
        pass

    @abstractmethod
    async def upsert_relationship(
        self, user_id: str, relationship: RelationshipCreate
    ) -> RelationshipResponse:
        """Idempotently insert or update a relationship edge with source evidence."""
        pass

    @abstractmethod
    async def get_entity(self, user_id: str, entity_id: str) -> Optional[EntityResponse]:
        """Fetch an entity by ID."""
        pass

    @abstractmethod
    async def get_entity_by_name(
        self, user_id: str, name: str, entity_type: Optional[str] = None
    ) -> Optional[EntityResponse]:
        """Lookup an entity by canonical name or alias."""
        pass

    @abstractmethod
    async def get_entity_relationships(
        self,
        user_id: str,
        entity_id: str,
        direction: str = "both",
        relationship_types: Optional[List[str]] = None,
        temporal_year: Optional[int] = None,
    ) -> List[RelationshipResponse]:
        """Fetch 1-hop relationships for a node."""
        pass

    @abstractmethod
    async def get_neighbors(
        self,
        user_id: str,
        entity_id: str,
        max_hops: int = 1,
        relationship_types: Optional[List[str]] = None,
        temporal_year: Optional[int] = None,
        limit: int = 50,
    ) -> GraphVisualizationResponse:
        """Traverse neighborhood up to max_hops and return nodes and edges for visualization."""
        pass

    @abstractmethod
    async def search_entities(
        self,
        user_id: str,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[EntityResponse]:
        """Search entities by name or alias substring/prefix."""
        pass

    @abstractmethod
    async def find_paths(
        self,
        user_id: str,
        start_entity_id: str,
        end_entity_id: Optional[str] = None,
        max_hops: int = 3,
        relationship_types: Optional[List[str]] = None,
        temporal_year: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Multi-hop path traversal between entities or outbound from an entity."""
        pass

    @abstractmethod
    async def get_full_graph(
        self, user_id: str, limit: int = 150
    ) -> GraphVisualizationResponse:
        """Retrieve graph visualization payload for user."""
        pass

    @abstractmethod
    async def delete_document_graph_data(self, user_id: str, document_id: str) -> None:
        """Remove entities and relationships whose only source evidence was the deleted document."""
        pass

    async def health_check(self) -> bool:
        """Verify graph store connection or readiness."""
        return True
