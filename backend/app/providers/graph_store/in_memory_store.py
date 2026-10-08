import asyncio
from collections import deque
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Dict, List, Optional, Set
from app.providers.graph_store.base import GraphStore
from app.schemas.graph import (
    EntityCreate,
    EntityResponse,
    GraphEdge,
    GraphNode,
    GraphVisualizationResponse,
    RelationshipCreate,
    RelationshipResponse,
)


def normalize_entity_name(name: str) -> str:
    """Normalize entity name for stable matching."""
    cleaned = name.strip()
    # Strip common corporate suffixes for matching
    cleaned = re.sub(
        r"\b(inc|inc\.|incorporated|corp|corp\.|corporation|llc|l\.l\.c\.|ltd|ltd\.|limited|co|co\.|company)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned or name.strip().lower()


def generate_node_id(user_id: str, entity_type: str, name: str) -> str:
    """Deterministic, idempotent ID for an entity node."""
    norm = normalize_entity_name(name)
    key = f"{user_id}:{entity_type.lower()}:{norm}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def generate_edge_id(user_id: str, source_id: str, target_id: str, rel_type: str) -> str:
    """Deterministic ID for a relationship edge."""
    key = f"{user_id}:{source_id}:{rel_type}:{target_id}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


class InMemoryGraphStore(GraphStore):
    """In-memory Knowledge Graph store for fast testing, offline local dev, and CI validation."""

    def __init__(self):
        # user_id -> {node_id -> dict}
        self._nodes: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # user_id -> {edge_id -> dict}
        self._edges: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # user_id -> {normalized_name -> node_id}
        self._name_index: Dict[str, Dict[str, str]] = {}
        self._lock = asyncio.Lock()

    def _ensure_user_store(self, user_id: str):
        if user_id not in self._nodes:
            self._nodes[user_id] = {}
            self._edges[user_id] = {}
            self._name_index[user_id] = {}

    async def initialize_schema(self) -> None:
        pass

    async def upsert_entity(self, user_id: str, entity: EntityCreate) -> EntityResponse:
        async with self._lock:
            self._ensure_user_store(user_id)
            user_nodes = self._nodes[user_id]
            user_index = self._name_index[user_id]

            norm_name = normalize_entity_name(entity.name)

            # Check if entity already exists via name index or aliases
            existing_id = user_index.get(norm_name)
            if not existing_id:
                for alias in entity.aliases:
                    norm_alias = normalize_entity_name(alias)
                    if norm_alias in user_index:
                        existing_id = user_index[norm_alias]
                        break

            if existing_id and existing_id in user_nodes:
                node = user_nodes[existing_id]
                # Update aliases and source docs
                existing_aliases = set(node.get("aliases", []))
                existing_aliases.update(entity.aliases)
                node["aliases"] = list(existing_aliases)
                if entity.source_document_id and entity.source_document_id not in node.get("source_document_ids", []):
                    node.setdefault("source_document_ids", []).append(entity.source_document_id)
                # Maximize confidence
                node["confidence"] = max(node.get("confidence", 0.0), entity.confidence)
                if entity.description and not node.get("description"):
                    node["description"] = entity.description
                node["properties"].update(entity.properties)
            else:
                node_id = generate_node_id(user_id, entity.type, entity.name)
                source_docs = [entity.source_document_id] if entity.source_document_id else []
                node = {
                    "id": node_id,
                    "user_id": user_id,
                    "name": entity.name.strip(),
                    "type": entity.type,
                    "aliases": list(set(entity.aliases)),
                    "confidence": entity.confidence,
                    "description": entity.description,
                    "properties": dict(entity.properties),
                    "source_document_ids": source_docs,
                    "created_at": datetime.now(timezone.utc),
                }
                user_nodes[node_id] = node
                user_index[norm_name] = node_id
                for alias in entity.aliases:
                    user_index[normalize_entity_name(alias)] = node_id

            return EntityResponse(
                id=node["id"],
                user_id=node["user_id"],
                name=node["name"],
                type=node["type"],
                aliases=node["aliases"],
                confidence=node["confidence"],
                description=node.get("description"),
                properties=node["properties"],
                source_document_ids=node.get("source_document_ids", []),
                created_at=node.get("created_at"),
            )

    async def upsert_relationship(
        self, user_id: str, relationship: RelationshipCreate
    ) -> RelationshipResponse:
        async with self._lock:
            self._ensure_user_store(user_id)
            user_nodes = self._nodes[user_id]
            user_edges = self._edges[user_id]

            # Require that source and target entities exist
            source_node = user_nodes.get(relationship.source_entity_id)
            target_node = user_nodes.get(relationship.target_entity_id)

            if not source_node or not target_node:
                raise ValueError(
                    f"Both source entity ({relationship.source_entity_id}) and target entity ({relationship.target_entity_id}) must exist before linking."
                )

            # Evidence validation: must have source document
            if not relationship.source_document_id:
                raise ValueError("Cannot create relationship without source evidence (source_document_id is required).")

            edge_id = generate_edge_id(
                user_id,
                relationship.source_entity_id,
                relationship.target_entity_id,
                relationship.relationship_type.upper(),
            )

            if edge_id in user_edges:
                edge = user_edges[edge_id]
                edge["confidence"] = max(edge.get("confidence", 0.0), relationship.confidence)
                if relationship.valid_from is not None:
                    edge["valid_from"] = relationship.valid_from
                if relationship.valid_to is not None:
                    edge["valid_to"] = relationship.valid_to
                edge["properties"].update(relationship.properties)
            else:
                edge = {
                    "id": edge_id,
                    "user_id": user_id,
                    "source_entity_id": relationship.source_entity_id,
                    "target_entity_id": relationship.target_entity_id,
                    "relationship_type": relationship.relationship_type.upper(),
                    "confidence": relationship.confidence,
                    "source_document_id": relationship.source_document_id,
                    "source_chunk_id": relationship.source_chunk_id,
                    "source_page": relationship.source_page,
                    "valid_from": relationship.valid_from,
                    "valid_to": relationship.valid_to,
                    "properties": dict(relationship.properties),
                    "created_at": datetime.now(timezone.utc),
                }
                user_edges[edge_id] = edge

            return RelationshipResponse(
                id=edge["id"],
                user_id=edge["user_id"],
                source_entity_id=edge["source_entity_id"],
                target_entity_id=edge["target_entity_id"],
                relationship_type=edge["relationship_type"],
                confidence=edge["confidence"],
                source_document_id=edge["source_document_id"],
                source_chunk_id=edge.get("source_chunk_id"),
                source_page=edge.get("source_page"),
                valid_from=edge.get("valid_from"),
                valid_to=edge.get("valid_to"),
                properties=edge["properties"],
                source_entity_name=source_node["name"],
                source_entity_type=source_node["type"],
                target_entity_name=target_node["name"],
                target_entity_type=target_node["type"],
                created_at=edge.get("created_at"),
            )

    async def get_entity(self, user_id: str, entity_id: str) -> Optional[EntityResponse]:
        async with self._lock:
            self._ensure_user_store(user_id)
            node = self._nodes[user_id].get(entity_id)
            if not node:
                return None
            return EntityResponse(**node)

    async def get_entity_by_name(
        self, user_id: str, name: str, entity_type: Optional[str] = None
    ) -> Optional[EntityResponse]:
        async with self._lock:
            self._ensure_user_store(user_id)
            norm_name = normalize_entity_name(name)
            node_id = self._name_index[user_id].get(norm_name)
            if node_id:
                node = self._nodes[user_id].get(node_id)
                if node and (not entity_type or node["type"].lower() == entity_type.lower()):
                    return EntityResponse(**node)
            # Fallback search if fuzzy
            for node in self._nodes[user_id].values():
                if entity_type and node["type"].lower() != entity_type.lower():
                    continue
                if node["name"].lower() == name.strip().lower() or name.strip().lower() in [
                    a.lower() for a in node.get("aliases", [])
                ]:
                    return EntityResponse(**node)
            return None

    async def get_entity_relationships(
        self,
        user_id: str,
        entity_id: str,
        direction: str = "both",
        relationship_types: Optional[List[str]] = None,
        temporal_year: Optional[int] = None,
    ) -> List[RelationshipResponse]:
        async with self._lock:
            self._ensure_user_store(user_id)
            user_edges = self._edges[user_id]
            user_nodes = self._nodes[user_id]
            results: List[RelationshipResponse] = []

            rel_filter = set([r.upper() for r in relationship_types]) if relationship_types else None

            for edge in user_edges.values():
                match = False
                if direction in ("outbound", "both") and edge["source_entity_id"] == entity_id:
                    match = True
                elif direction in ("inbound", "both") and edge["target_entity_id"] == entity_id:
                    match = True

                if not match:
                    continue

                if rel_filter and edge["relationship_type"] not in rel_filter:
                    continue

                if temporal_year is not None:
                    vf = edge.get("valid_from")
                    vt = edge.get("valid_to")
                    if vf is not None and vf > temporal_year:
                        continue
                    if vt is not None and vt < temporal_year:
                        continue

                src_node = user_nodes.get(edge["source_entity_id"], {})
                tgt_node = user_nodes.get(edge["target_entity_id"], {})

                results.append(
                    RelationshipResponse(
                        id=edge["id"],
                        user_id=user_id,
                        source_entity_id=edge["source_entity_id"],
                        target_entity_id=edge["target_entity_id"],
                        relationship_type=edge["relationship_type"],
                        confidence=edge["confidence"],
                        source_document_id=edge["source_document_id"],
                        source_chunk_id=edge.get("source_chunk_id"),
                        source_page=edge.get("source_page"),
                        valid_from=edge.get("valid_from"),
                        valid_to=edge.get("valid_to"),
                        properties=edge.get("properties", {}),
                        source_entity_name=src_node.get("name"),
                        source_entity_type=src_node.get("type"),
                        target_entity_name=tgt_node.get("name"),
                        target_entity_type=tgt_node.get("type"),
                        created_at=edge.get("created_at"),
                    )
                )

            return results

    async def get_neighbors(
        self,
        user_id: str,
        entity_id: str,
        max_hops: int = 1,
        relationship_types: Optional[List[str]] = None,
        temporal_year: Optional[int] = None,
        limit: int = 50,
    ) -> GraphVisualizationResponse:
        async with self._lock:
            self._ensure_user_store(user_id)
            user_nodes = self._nodes[user_id]
            user_edges = self._edges[user_id]

            if entity_id not in user_nodes:
                return GraphVisualizationResponse(nodes=[], edges=[])

            visited_node_ids: Set[str] = {entity_id}
            matched_edges: List[GraphEdge] = []
            queue = deque([(entity_id, 0)])

            rel_filter = set([r.upper() for r in relationship_types]) if relationship_types else None

            while queue and len(visited_node_ids) < limit:
                curr_node_id, hops = queue.popleft()
                if hops >= max_hops:
                    continue

                for edge in user_edges.values():
                    if rel_filter and edge["relationship_type"] not in rel_filter:
                        continue
                    if temporal_year is not None:
                        vf = edge.get("valid_from")
                        vt = edge.get("valid_to")
                        if vf is not None and vf > temporal_year:
                            continue
                        if vt is not None and vt < temporal_year:
                            continue

                    neighbor_id = None
                    if edge["source_entity_id"] == curr_node_id:
                        neighbor_id = edge["target_entity_id"]
                    elif edge["target_entity_id"] == curr_node_id:
                        neighbor_id = edge["source_entity_id"]

                    if neighbor_id and neighbor_id in user_nodes:
                        edge_obj = GraphEdge(
                            id=edge["id"],
                            source=edge["source_entity_id"],
                            target=edge["target_entity_id"],
                            relationship=edge["relationship_type"],
                            confidence=edge["confidence"],
                            source_document=edge.get("source_document_id"),
                            valid_from=edge.get("valid_from"),
                            valid_to=edge.get("valid_to"),
                            metadata=edge.get("properties", {}),
                        )
                        if not any(e.id == edge_obj.id for e in matched_edges):
                            matched_edges.append(edge_obj)

                        if neighbor_id not in visited_node_ids:
                            visited_node_ids.add(neighbor_id)
                            queue.append((neighbor_id, hops + 1))

            matched_nodes = [
                GraphNode(
                    id=nid,
                    label=user_nodes[nid]["name"],
                    type=user_nodes[nid]["type"],
                    metadata={
                        "confidence": user_nodes[nid]["confidence"],
                        "aliases": user_nodes[nid]["aliases"],
                        "description": user_nodes[nid].get("description"),
                        "properties": user_nodes[nid].get("properties", {}),
                    },
                )
                for nid in visited_node_ids
                if nid in user_nodes
            ]

            return GraphVisualizationResponse(nodes=matched_nodes, edges=matched_edges)

    async def search_entities(
        self,
        user_id: str,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[EntityResponse]:
        async with self._lock:
            self._ensure_user_store(user_id)
            user_nodes = self._nodes[user_id]
            q_clean = query.strip().lower()

            results: List[EntityResponse] = []
            type_filter = set([t.lower() for t in entity_types]) if entity_types else None

            for node in user_nodes.values():
                if type_filter and node["type"].lower() not in type_filter:
                    continue

                name_match = q_clean in node["name"].lower()
                alias_match = any(q_clean in a.lower() for a in node.get("aliases", []))

                if name_match or alias_match:
                    results.append(EntityResponse(**node))
                    if len(results) >= limit:
                        break

            return results

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
        async with self._lock:
            self._ensure_user_store(user_id)
            user_nodes = self._nodes[user_id]
            user_edges = self._edges[user_id]

            if start_entity_id not in user_nodes:
                return []

            rel_filter = set([r.upper() for r in relationship_types]) if relationship_types else None
            paths: List[Dict[str, Any]] = []

            # Path queue: list of (current_node_id, path_nodes_list, path_edges_list)
            start_node = user_nodes[start_entity_id]
            queue = deque([(start_entity_id, [start_node], [])])

            while queue and len(paths) < limit:
                curr_id, path_nodes, path_edges = queue.popleft()

                if end_entity_id and curr_id == end_entity_id and len(path_edges) > 0:
                    paths.append({
                        "length": len(path_edges),
                        "nodes": [n["name"] for n in path_nodes],
                        "node_types": [n["type"] for n in path_nodes],
                        "relationships": [e["relationship_type"] for e in path_edges],
                        "edges": path_edges,
                    })
                    continue

                if not end_entity_id and len(path_edges) > 0:
                    paths.append({
                        "length": len(path_edges),
                        "nodes": [n["name"] for n in path_nodes],
                        "node_types": [n["type"] for n in path_nodes],
                        "relationships": [e["relationship_type"] for e in path_edges],
                        "edges": path_edges,
                    })

                if len(path_edges) >= max_hops:
                    continue

                curr_visited = {n["id"] for n in path_nodes}

                for edge in user_edges.values():
                    nxt_id = None
                    if edge["source_entity_id"] == curr_id:
                        nxt_id = edge["target_entity_id"]
                    elif edge["target_entity_id"] == curr_id:
                        nxt_id = edge["source_entity_id"]

                    if not nxt_id:
                        continue

                    if rel_filter and edge["relationship_type"] not in rel_filter:
                        continue
                    if temporal_year is not None:
                        vf = edge.get("valid_from")
                        vt = edge.get("valid_to")
                        if vf is not None and vf > temporal_year:
                            continue
                        if vt is not None and vt < temporal_year:
                            continue

                    if nxt_id not in curr_visited and nxt_id in user_nodes:
                        nxt_node = user_nodes[nxt_id]
                        queue.append((
                            nxt_id,
                            path_nodes + [nxt_node],
                            path_edges + [edge],
                        ))


            return paths

    async def get_full_graph(
        self, user_id: str, limit: int = 150
    ) -> GraphVisualizationResponse:
        async with self._lock:
            self._ensure_user_store(user_id)
            user_nodes = self._nodes[user_id]
            user_edges = self._edges[user_id]

            selected_nodes = list(user_nodes.values())[:limit]
            selected_node_ids = {n["id"] for n in selected_nodes}

            nodes = [
                GraphNode(
                    id=n["id"],
                    label=n["name"],
                    type=n["type"],
                    metadata={
                        "confidence": n["confidence"],
                        "aliases": n["aliases"],
                        "description": n.get("description"),
                        "properties": n.get("properties", {}),
                    },
                )
                for n in selected_nodes
            ]

            edges = [
                GraphEdge(
                    id=e["id"],
                    source=e["source_entity_id"],
                    target=e["target_entity_id"],
                    relationship=e["relationship_type"],
                    confidence=e["confidence"],
                    source_document=e.get("source_document_id"),
                    valid_from=e.get("valid_from"),
                    valid_to=e.get("valid_to"),
                    metadata=e.get("properties", {}),
                )
                for e in user_edges.values()
                if e["source_entity_id"] in selected_node_ids and e["target_entity_id"] in selected_node_ids
            ]

            return GraphVisualizationResponse(nodes=nodes, edges=edges)

    async def delete_document_graph_data(self, user_id: str, document_id: str) -> None:
        async with self._lock:
            self._ensure_user_store(user_id)
            user_edges = self._edges[user_id]
            user_nodes = self._nodes[user_id]

            # Remove edges tied solely to this document
            edges_to_remove = [
                eid for eid, e in user_edges.items()
                if e.get("source_document_id") == document_id
            ]
            for eid in edges_to_remove:
                del user_edges[eid]

            # Remove doc id from nodes, and prune if orphaned
            nodes_to_remove = []
            for nid, node in user_nodes.items():
                if document_id in node.get("source_document_ids", []):
                    node["source_document_ids"].remove(document_id)
                    if not node["source_document_ids"]:
                        # check if node is in any remaining edge
                        has_edges = any(
                            e["source_entity_id"] == nid or e["target_entity_id"] == nid
                            for e in user_edges.values()
                        )
                        if not has_edges:
                            nodes_to_remove.append(nid)

            for nid in nodes_to_remove:
                node_name = user_nodes[nid]["name"]
                del user_nodes[nid]
                norm_name = normalize_entity_name(node_name)
                if norm_name in self._name_index[user_id]:
                    del self._name_index[user_id][norm_name]
