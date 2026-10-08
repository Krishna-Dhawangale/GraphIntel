from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.logging import log_event, logger
from app.providers.graph_store.base import GraphStore
from app.providers.graph_store.factory import get_graph_store
from app.schemas.graph import (
    EntityCreate,
    EntityDetailResponse,
    EntityResponse,
    GraphNode,
    GraphSearchRequest,
    GraphVisualizationResponse,
    RelationshipCreate,
    RelationshipResponse,
)
from app.services.entity_extractor import BaseEntityExtractor, LLMEntityExtractor
from app.services.entity_resolver import EntityResolver


class GraphService:
    """Enterprise Knowledge Graph service for GraphIntel."""

    def __init__(
        self,
        graph_store: Optional[GraphStore] = None,
        extractor: Optional[BaseEntityExtractor] = None,
        resolver: Optional[EntityResolver] = None,
    ):
        self.store = graph_store or get_graph_store()
        self.extractor = extractor or LLMEntityExtractor()
        self.resolver = resolver or EntityResolver()

    async def sync_chunk_to_graph(
        self,
        user_id: str,
        document_id: str,
        chunk_id: str,
        text: str,
        page_number: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Extract entities, resolve against existing user graph, and idempotently upsert to GraphStore.
        """
        raw_entities, raw_rels = await self.extractor.extract(
            text=text,
            document_id=document_id,
            chunk_id=chunk_id,
            page_number=page_number,
        )

        if not raw_entities and not raw_rels:
            return {"entities_synced": 0, "relationships_synced": 0}

        # Retrieve existing user entities for resolution context
        existing = await self.store.search_entities(user_id=user_id, query="", limit=200)
        existing_dicts = [{"name": e.name, "type": e.type, "aliases": e.aliases} for e in existing]

        # Map extracted raw names to resolved canonical EntityResponse
        name_to_entity: Dict[str, EntityResponse] = {}

        for raw_ent in raw_entities:
            canonical_name, new_aliases, res_conf = self.resolver.resolve(
                name=raw_ent.name,
                entity_type=raw_ent.type,
                existing_entities=existing_dicts,
            )

            ent_to_upsert = EntityCreate(
                name=canonical_name,
                type=raw_ent.type,
                aliases=list(set(raw_ent.aliases + new_aliases)),
                confidence=min(raw_ent.confidence, res_conf),
                description=raw_ent.description,
                source_document_id=document_id,
                source_chunk_id=chunk_id,
                source_page=page_number,
            )

            resolved_resp = await self.store.upsert_entity(user_id, ent_to_upsert)
            name_to_entity[raw_ent.name.strip().lower()] = resolved_resp
            name_to_entity[canonical_name.strip().lower()] = resolved_resp

        # Link relationships with resolved entity IDs
        rels_synced = 0
        for rel in raw_rels:
            src_key = rel.source_entity_id.strip().lower()
            tgt_key = rel.target_entity_id.strip().lower()

            src_entity = name_to_entity.get(src_key)
            tgt_entity = name_to_entity.get(tgt_key)

            # If not in local batch, try lookup in store
            if not src_entity:
                src_entity = await self.store.get_entity_by_name(user_id, rel.source_entity_id)
            if not tgt_entity:
                tgt_entity = await self.store.get_entity_by_name(user_id, rel.target_entity_id)

            if src_entity and tgt_entity and src_entity.id != tgt_entity.id:
                rel_create = RelationshipCreate(
                    source_entity_id=src_entity.id,
                    target_entity_id=tgt_entity.id,
                    relationship_type=rel.relationship_type,
                    confidence=rel.confidence,
                    source_document_id=document_id,
                    source_chunk_id=chunk_id,
                    source_page=page_number,
                    valid_from=rel.valid_from,
                    valid_to=rel.valid_to,
                    properties=rel.properties,
                )
                await self.store.upsert_relationship(user_id, rel_create)
                rels_synced += 1

        log_event(
            "graph_chunk_synced",
            f"Synced {len(name_to_entity)} entities and {rels_synced} relationships for chunk {chunk_id}",
            user_id=user_id,
            document_id=document_id,
            chunk_id=chunk_id,
        )

        return {
            "entities_synced": len(name_to_entity),
            "relationships_synced": rels_synced,
        }

    async def get_entity_detail(
        self, user_id: str, entity_id: str
    ) -> Optional[EntityDetailResponse]:
        """Fetch entity, all its incident relationships, and 1-hop neighbor nodes."""
        entity = await self.store.get_entity(user_id, entity_id)
        if not entity:
            return None

        relationships = await self.store.get_entity_relationships(user_id, entity_id)
        neighbors_vis = await self.store.get_neighbors(user_id, entity_id, max_hops=1)

        return EntityDetailResponse(
            entity=entity,
            relationships=relationships,
            neighbors=neighbors_vis.nodes,
        )

    async def get_entity_relationships(
        self,
        user_id: str,
        entity_id: str,
        direction: str = "both",
        relationship_types: Optional[List[str]] = None,
        temporal_year: Optional[int] = None,
    ) -> List[RelationshipResponse]:
        return await self.store.get_entity_relationships(
            user_id=user_id,
            entity_id=entity_id,
            direction=direction,
            relationship_types=relationship_types,
            temporal_year=temporal_year,
        )

    async def get_neighbors(
        self,
        user_id: str,
        entity_id: str,
        max_hops: int = 1,
        relationship_types: Optional[List[str]] = None,
        temporal_year: Optional[int] = None,
    ) -> GraphVisualizationResponse:
        hops = min(max(1, max_hops), settings.MAX_GRAPH_HOPS)
        return await self.store.get_neighbors(
            user_id=user_id,
            entity_id=entity_id,
            max_hops=hops,
            relationship_types=relationship_types,
            temporal_year=temporal_year,
        )

    async def search_entities(
        self,
        user_id: str,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[EntityResponse]:
        return await self.store.search_entities(
            user_id=user_id,
            query=query,
            entity_types=entity_types,
            limit=limit,
        )

    async def get_graph_visualization(
        self, user_id: str, limit: int = 150
    ) -> GraphVisualizationResponse:
        """Fetch full graph visualization payload."""
        return await self.store.get_full_graph(user_id=user_id, limit=limit)
