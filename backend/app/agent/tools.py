from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.providers.graph_store.factory import get_graph_store
from app.schemas.graph import EntityResponse
from app.schemas.query import EvidenceItem, GraphPathInfo, RetrievedChunk
from app.services.graph_retriever import GraphRetriever
from app.services.retrieval_service import RetrievalService


class AgentTools:
    """Safe, tenant-isolated tools for LangGraph Agentic RAG workflow."""

    def __init__(self):
        self.retrieval_service = RetrievalService()
        self.graph_store = get_graph_store()
        self.graph_retriever = GraphRetriever(store=self.graph_store)

    async def vector_search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        filters: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        """Execute vector semantic search strictly within user's documents."""
        limit = min(max(1, top_k), 20)
        return await self.retrieval_service.retrieve(
            query=query,
            user_id=user_id,
            top_k=limit,
            filters=filters,
        )

    async def graph_search(
        self,
        user_id: str,
        entities: List[str],
        relationships: Optional[List[str]] = None,
        max_hops: int = 2,
        temporal_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute safe knowledge graph path and relationship traversal."""
        hops = min(max(1, max_hops), settings.MAX_GRAPH_HOPS)
        evidence, paths, matched = await self.graph_retriever.retrieve(
            user_id=user_id,
            entities=entities,
            relationships=relationships,
            max_hops=hops,
            temporal_year=temporal_year,
            limit=20,
        )
        return {
            "evidence": evidence,
            "paths": paths,
            "matched_entities": matched,
        }

    async def entity_lookup(self, user_id: str, name: str) -> Optional[EntityResponse]:
        """Lookup entity canonical details in knowledge graph."""
        return await self.graph_store.get_entity_by_name(user_id=user_id, name=name)

    async def search_entities(self, user_id: str, query: str, limit: int = 10) -> List[EntityResponse]:
        """Search entities by keyword/prefix."""
        return await self.graph_store.search_entities(user_id=user_id, query=query, limit=min(limit, 20))
