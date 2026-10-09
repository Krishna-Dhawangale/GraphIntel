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

    async def sync_chunks_to_graph(
        self,
        user_id: str,
        document_id: str,
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        High-performance batch entity extraction, resolution, and graph synchronization across document chunks.
        """
        if not chunks:
            return {"entities_synced": 0, "relationships_synced": 0}

        import asyncio

        # 1. Parallel / asynchronous extraction across chunks
        extraction_tasks = []
        for c in chunks:
            text = c.get("text", "")
            chunk_id = c.get("chunk_id", "")
            page_num = c.get("page_number")
            extraction_tasks.append(
                self.extractor.extract(
                    text=text,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    page_number=page_num,
                )
            )

        extracted_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        all_raw_entities: List[EntityCreate] = []
        all_raw_rels: List[RelationshipCreate] = []

        for res in extracted_results:
            if isinstance(res, Exception):
                logger.warning(f"Error extracting entities from chunk: {res}")
                continue
            if isinstance(res, tuple) and len(res) == 2:
                ents, rels = res
                all_raw_entities.extend(ents)
                all_raw_rels.extend(rels)

        if not all_raw_entities and not all_raw_rels:
            return {"entities_synced": 0, "relationships_synced": 0}

        # 2. Fetch existing entities ONCE for the entire document batch
        existing = await self.store.search_entities(user_id=user_id, query="", limit=500)
        existing_dicts = [{"name": e.name, "type": e.type, "aliases": e.aliases} for e in existing]

        # 3. Resolve entities with shared in-memory dictionary
        name_to_entity: Dict[str, EntityResponse] = {}
        unique_canonical_upserts: Dict[str, EntityCreate] = {}

        for raw_ent in all_raw_entities:
            canonical_name, new_aliases, res_conf = self.resolver.resolve(
                name=raw_ent.name,
                entity_type=raw_ent.type,
                existing_entities=existing_dicts,
            )

            canon_key = canonical_name.strip().lower()
            if canon_key not in unique_canonical_upserts:
                ent_to_upsert = EntityCreate(
                    name=canonical_name,
                    type=raw_ent.type,
                    aliases=list(set(raw_ent.aliases + new_aliases)),
                    confidence=min(raw_ent.confidence, res_conf),
                    description=raw_ent.description,
                    source_document_id=document_id,
                    source_chunk_id=raw_ent.source_chunk_id,
                    source_page=raw_ent.source_page,
                )
                unique_canonical_upserts[canon_key] = ent_to_upsert
            else:
                existing_create = unique_canonical_upserts[canon_key]
                existing_create.aliases = list(set(existing_create.aliases + raw_ent.aliases + new_aliases))

        # Upsert unique canonical entities
        for canon_key, ent_create in unique_canonical_upserts.items():
            resolved_resp = await self.store.upsert_entity(user_id, ent_create)
            name_to_entity[ent_create.name.strip().lower()] = resolved_resp
            name_to_entity[canon_key] = resolved_resp
            existing_dicts.append({
                "name": resolved_resp.name,
                "type": resolved_resp.type,
                "aliases": resolved_resp.aliases,
            })

        # Also map all raw aliases to the resolved response
        for raw_ent in all_raw_entities:
            raw_key = raw_ent.name.strip().lower()
            if raw_key not in name_to_entity:
                canonical_name, _, _ = self.resolver.resolve(
                    name=raw_ent.name,
                    entity_type=raw_ent.type,
                    existing_entities=existing_dicts,
                )
                if canonical_name.strip().lower() in name_to_entity:
                    name_to_entity[raw_key] = name_to_entity[canonical_name.strip().lower()]

        # 4. Link relationships with resolved entity IDs
        rels_synced = 0
        seen_rel_keys = set()

        for rel in all_raw_rels:
            src_key = rel.source_entity_id.strip().lower()
            tgt_key = rel.target_entity_id.strip().lower()

            src_entity = name_to_entity.get(src_key)
            tgt_entity = name_to_entity.get(tgt_key)

            if not src_entity:
                src_entity = await self.store.get_entity_by_name(user_id, rel.source_entity_id)
                if src_entity:
                    name_to_entity[src_key] = src_entity
            if not tgt_entity:
                tgt_entity = await self.store.get_entity_by_name(user_id, rel.target_entity_id)
                if tgt_entity:
                    name_to_entity[tgt_key] = tgt_entity

            if src_entity and tgt_entity and src_entity.id != tgt_entity.id:
                rel_dedup_key = (src_entity.id, tgt_entity.id, rel.relationship_type.upper(), rel.valid_from)
                if rel_dedup_key in seen_rel_keys:
                    continue
                seen_rel_keys.add(rel_dedup_key)

                rel_create = RelationshipCreate(
                    source_entity_id=src_entity.id,
                    target_entity_id=tgt_entity.id,
                    relationship_type=rel.relationship_type,
                    confidence=rel.confidence,
                    source_document_id=document_id,
                    source_chunk_id=rel.source_chunk_id,
                    source_page=rel.source_page,
                    valid_from=rel.valid_from,
                    valid_to=rel.valid_to,
                    properties=rel.properties,
                )
                await self.store.upsert_relationship(user_id, rel_create)
                rels_synced += 1

        log_event(
            "graph_batch_synced",
            f"Batch synced {len(unique_canonical_upserts)} entities and {rels_synced} relationships for document {document_id}",
            user_id=user_id,
            document_id=document_id,
            total_chunks=len(chunks),
        )

        return {
            "entities_synced": len(unique_canonical_upserts),
            "relationships_synced": rels_synced,
        }

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
        return await self.sync_chunks_to_graph(
            user_id=user_id,
            document_id=document_id,
            chunks=[{"chunk_id": chunk_id, "text": text, "page_number": page_number}],
        )

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
