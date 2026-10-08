from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.providers.graph_store.base import GraphStore
from app.providers.graph_store.factory import get_graph_store
from app.schemas.graph import EntityResponse, RelationshipResponse
from app.schemas.query import EvidenceItem, GraphPathInfo


class GraphRetriever:
    """Safe, parameterized Graph retriever supporting 1-hop, 2-hop, and multi-hop traversal with temporal filtering."""

    def __init__(self, store: Optional[GraphStore] = None):
        self.store = store or get_graph_store()

    async def retrieve(
        self,
        user_id: str,
        entities: List[str],
        relationships: Optional[List[str]] = None,
        max_hops: int = 1,
        temporal_year: Optional[int] = None,
        limit: int = 20,
    ) -> Tuple[List[EvidenceItem], List[GraphPathInfo], List[str]]:
        """
        Executes safe graph retrieval.
        Returns: (evidence_items, graph_paths, matched_entity_names)
        """
        evidence_items: List[EvidenceItem] = []
        graph_paths: List[GraphPathInfo] = []
        matched_entity_names: List[str] = []

        hops = min(max(1, max_hops), settings.MAX_GRAPH_HOPS)

        # 1. Resolve seed entities in the knowledge graph
        seed_entities: List[EntityResponse] = []
        for name in entities:
            # First try exact/alias lookup
            found = await self.store.get_entity_by_name(user_id=user_id, name=name)
            if not found:
                # Search prefix/substring
                search_res = await self.store.search_entities(user_id=user_id, query=name, limit=3)
                if search_res:
                    found = search_res[0]

            if found and found.id not in [e.id for e in seed_entities]:
                seed_entities.append(found)
                matched_entity_names.append(found.name)

        # If no specific entities found by name, search broad query match
        if not seed_entities and entities:
            for term in entities[:2]:
                res = await self.store.search_entities(user_id=user_id, query=term, limit=5)
                for e in res:
                    if e.id not in [se.id for se in seed_entities]:
                        seed_entities.append(e)
                        matched_entity_names.append(e.name)

        # 2. Traverse relationships for each seed entity
        seen_edges = set()
        for ent in seed_entities:
            # Fetch direct relationships
            direct_rels = await self.store.get_entity_relationships(
                user_id=user_id,
                entity_id=ent.id,
                relationship_types=relationships,
                temporal_year=temporal_year,
            )
            # If no relationships found matching the strict filter, fallback to all incident relationships
            if not direct_rels and relationships:
                direct_rels = await self.store.get_entity_relationships(
                    user_id=user_id,
                    entity_id=ent.id,
                    relationship_types=None,
                    temporal_year=temporal_year,
                )

            for rel in direct_rels:
                edge_sig = f"{rel.source_entity_id}-{rel.relationship_type}-{rel.target_entity_id}"
                if edge_sig not in seen_edges:
                    seen_edges.add(edge_sig)

                    # Build graph evidence item
                    content = (
                        f"Knowledge Graph Fact: {rel.source_entity_name or ent.name} "
                        f"{rel.relationship_type} {rel.target_entity_name} "
                    )
                    if rel.valid_from or rel.valid_to:
                        content += f"({rel.valid_from or 'historical'} to {rel.valid_to or 'present'}) "
                    content += f"[Confidence: {rel.confidence:.2f}]"

                    evidence_items.append(
                        EvidenceItem(
                            type="graph",
                            content=content,
                            entity=rel.source_entity_name or ent.name,
                            relationship=rel.relationship_type,
                            target=rel.target_entity_name,
                            source_document=rel.source_document_id,
                            page=rel.source_page,
                            confidence=rel.confidence,
                            valid_from=rel.valid_from,
                            valid_to=rel.valid_to,
                        )
                    )

            # 3. Multi-hop path finding if hops > 1 (explore open paths from seed entity)
            if hops > 1:
                paths = await self.store.find_paths(
                    user_id=user_id,
                    start_entity_id=ent.id,
                    max_hops=hops,
                    relationship_types=None,
                    temporal_year=temporal_year,
                    limit=limit,
                )


                for p in paths:
                    evidence_docs = [
                        e.get("source_document_id") for e in p.get("edges", []) if e.get("source_document_id")
                    ]
                    graph_paths.append(
                        GraphPathInfo(
                            length=p["length"],
                            nodes=p["nodes"],
                            node_types=p["node_types"],
                            relationships=p["relationships"],
                            evidence_docs=list(set(evidence_docs)),
                        )
                    )

                    path_desc = " -> ".join(
                        f"({p['nodes'][i]}:{p['node_types'][i]}) -[{p['relationships'][i]}]-> ({p['nodes'][i+1]}:{p['node_types'][i+1]})"
                        for i in range(len(p["relationships"]))
                    )

                    evidence_items.append(
                        EvidenceItem(
                            type="graph",
                            content=f"Knowledge Graph Multi-Hop Path: {path_desc}",
                            entity=p["nodes"][0] if p["nodes"] else None,
                            target=p["nodes"][-1] if p["nodes"] else None,
                            source_document=evidence_docs[0] if evidence_docs else None,
                            confidence=0.90,
                        )
                    )

        return evidence_items, graph_paths, matched_entity_names
