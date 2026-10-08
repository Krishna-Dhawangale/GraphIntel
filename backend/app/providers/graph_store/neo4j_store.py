import asyncio
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Dict, List, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable, DriverError

from app.core.config import settings
from app.core.logging import logger
from app.providers.graph_store.base import GraphStore
from app.providers.graph_store.in_memory_store import (
    InMemoryGraphStore,
    generate_edge_id,
    generate_node_id,
    normalize_entity_name,
)
from app.schemas.graph import (
    EntityCreate,
    EntityResponse,
    GraphEdge,
    GraphNode,
    GraphVisualizationResponse,
    NodeType,
    RelationshipCreate,
    RelationshipResponse,
    RelationshipType,
)

ALLOWED_LABELS = {t.value for t in NodeType}
ALLOWED_RELATIONSHIPS = {r.value for r in RelationshipType}


class Neo4jGraphStore(GraphStore):
    """Production Neo4j Knowledge Graph store with asynchronous driver and safe Cypher execution,
    featuring transparent fallback to InMemoryGraphStore if the Neo4j instance is offline or unreachable."""

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.uri = uri or settings.NEO4J_URI
        self.username = username or settings.NEO4J_USERNAME
        self.password = password or settings.NEO4J_PASSWORD
        self.database = database or settings.NEO4J_DATABASE
        self._driver: Optional[AsyncDriver] = None
        self._initialized = False
        self._fallback = InMemoryGraphStore()
        self._is_available: Optional[bool] = None

    async def is_available(self) -> bool:
        if self._is_available is not None:
            return self._is_available

        try:
            driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                connection_timeout=2.0,
            )
            # Short test
            await asyncio.wait_for(driver.verify_connectivity(), timeout=2.0)
            self._driver = driver
            self._is_available = True
            if not self._initialized:
                await self.initialize_schema()
                self._initialized = True
            return True
        except Exception as e:
            logger.info(
                f"Neo4j is not currently reachable at {self.uri} ({e}). Using resilient in-memory graph store."
            )
            self._is_available = False
            return False

    async def get_driver(self) -> Optional[AsyncDriver]:
        if await self.is_available():
            return self._driver
        return None

    async def close(self):
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def initialize_schema(self) -> None:
        """Create constraints and indexes in Neo4j."""
        if not self._driver:
            return
        try:
            async with self._driver.session(database=self.database) as session:
                await session.run(
                    "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
                    "FOR (n:Entity) REQUIRE (n.user_id, n.id) IS UNIQUE"
                )
                await session.run(
                    "CREATE INDEX entity_name_idx IF NOT EXISTS "
                    "FOR (n:Entity) ON (n.name)"
                )
                await session.run(
                    "CREATE INDEX entity_user_type_idx IF NOT EXISTS "
                    "FOR (n:Entity) ON (n.user_id, n.type)"
                )
                for label in ALLOWED_LABELS:
                    query = (
                        f"CREATE CONSTRAINT {label.lower()}_user_id_unique IF NOT EXISTS "
                        f"FOR (n:{label}) REQUIRE (n.user_id, n.id) IS UNIQUE"
                    )
                    await session.run(query)
            logger.info("Neo4j schema constraints and indexes initialized successfully.")
        except Exception as e:
            logger.warning(f"Neo4j schema initialization warning: {e}")

    async def upsert_entity(self, user_id: str, entity: EntityCreate) -> EntityResponse:
        driver = await self.get_driver()
        if not driver:
            return await self._fallback.upsert_entity(user_id, entity)

        clean_type = entity.type if entity.type in ALLOWED_LABELS else "Entity"
        node_id = generate_node_id(user_id, clean_type, entity.name)
        norm_name = normalize_entity_name(entity.name)

        cypher = f"""
        MERGE (n:Entity {{id: $id, user_id: $user_id}})
        ON CREATE SET
            n:{clean_type},
            n.name = $name,
            n.type = $type,
            n.normalized_name = $norm_name,
            n.aliases = $aliases,
            n.confidence = $confidence,
            n.description = $description,
            n.source_document_ids = $source_docs,
            n.created_at = datetime()
        ON MATCH SET
            n.confidence = CASE WHEN $confidence > n.confidence THEN $confidence ELSE n.confidence END,
            n.description = coalesce(n.description, $description)
        RETURN n
        """

        source_docs = [entity.source_document_id] if entity.source_document_id else []
        params = {
            "id": node_id,
            "user_id": user_id,
            "name": entity.name.strip(),
            "type": clean_type,
            "norm_name": norm_name,
            "aliases": list(set(entity.aliases)),
            "confidence": float(entity.confidence),
            "description": entity.description or "",
            "source_docs": source_docs,
        }

        try:
            async with driver.session(database=self.database) as session:
                result = await session.run(cypher, params)
                record = await result.single()
                if not record:
                    raise RuntimeError(f"Failed to upsert entity {entity.name}")
                node = record["n"]

                return EntityResponse(
                    id=node["id"],
                    user_id=node["user_id"],
                    name=node["name"],
                    type=node["type"],
                    aliases=list(node.get("aliases", [])),
                    confidence=float(node.get("confidence", 1.0)),
                    description=node.get("description"),
                    properties={},
                    source_document_ids=list(node.get("source_document_ids", [])),
                    created_at=datetime.now(timezone.utc),
                )
        except (ServiceUnavailable, DriverError):
            self._is_available = False
            return await self._fallback.upsert_entity(user_id, entity)

    async def upsert_relationship(
        self, user_id: str, relationship: RelationshipCreate
    ) -> RelationshipResponse:
        driver = await self.get_driver()
        if not driver:
            return await self._fallback.upsert_relationship(user_id, relationship)

        rel_type = relationship.relationship_type.upper()
        if rel_type not in ALLOWED_RELATIONSHIPS:
            rel_type = "RELATED_TO"

        edge_id = generate_edge_id(
            user_id,
            relationship.source_entity_id,
            relationship.target_entity_id,
            rel_type,
        )

        cypher = f"""
        MATCH (src:Entity {{id: $source_id, user_id: $user_id}})
        MATCH (tgt:Entity {{id: $target_id, user_id: $user_id}})
        MERGE (src)-[r:{rel_type} {{id: $edge_id, user_id: $user_id}}]->(tgt)
        ON CREATE SET
            r.confidence = $confidence,
            r.source_document_id = $source_document_id,
            r.source_chunk_id = $source_chunk_id,
            r.source_page = $source_page,
            r.valid_from = $valid_from,
            r.valid_to = $valid_to,
            r.created_at = datetime()
        ON MATCH SET
            r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END,
            r.valid_from = coalesce($valid_from, r.valid_from),
            r.valid_to = coalesce($valid_to, r.valid_to)
        RETURN r, src.name AS src_name, src.type AS src_type, tgt.name AS tgt_name, tgt.type AS tgt_type
        """

        params = {
            "source_id": relationship.source_entity_id,
            "target_id": relationship.target_entity_id,
            "user_id": user_id,
            "edge_id": edge_id,
            "confidence": float(relationship.confidence),
            "source_document_id": relationship.source_document_id,
            "source_chunk_id": relationship.source_chunk_id or "",
            "source_page": relationship.source_page,
            "valid_from": relationship.valid_from,
            "valid_to": relationship.valid_to,
        }

        try:
            async with driver.session(database=self.database) as session:
                result = await session.run(cypher, params)
                record = await result.single()
                if not record:
                    raise ValueError("Could not create relationship: source or target entity not found.")
                r = record["r"]
                return RelationshipResponse(
                    id=r["id"],
                    user_id=r["user_id"],
                    source_entity_id=relationship.source_entity_id,
                    target_entity_id=relationship.target_entity_id,
                    relationship_type=rel_type,
                    confidence=float(r.get("confidence", 1.0)),
                    source_document_id=r.get("source_document_id"),
                    source_chunk_id=r.get("source_chunk_id"),
                    source_page=r.get("source_page"),
                    valid_from=r.get("valid_from"),
                    valid_to=r.get("valid_to"),
                    properties={},
                    source_entity_name=record["src_name"],
                    source_entity_type=record["src_type"],
                    target_entity_name=record["tgt_name"],
                    target_entity_type=record["tgt_type"],
                    created_at=datetime.now(timezone.utc),
                )
        except (ServiceUnavailable, DriverError):
            self._is_available = False
            return await self._fallback.upsert_relationship(user_id, relationship)

    async def get_entity(self, user_id: str, entity_id: str) -> Optional[EntityResponse]:
        driver = await self.get_driver()
        if not driver:
            return await self._fallback.get_entity(user_id, entity_id)

        cypher = "MATCH (n:Entity {id: $id, user_id: $user_id}) RETURN n"
        try:
            async with driver.session(database=self.database) as session:
                result = await session.run(cypher, {"id": entity_id, "user_id": user_id})
                record = await result.single()
                if not record:
                    return None
                n = record["n"]
                return EntityResponse(
                    id=n["id"],
                    user_id=n["user_id"],
                    name=n["name"],
                    type=n["type"],
                    aliases=list(n.get("aliases", [])),
                    confidence=float(n.get("confidence", 1.0)),
                    description=n.get("description"),
                    properties={},
                    source_document_ids=list(n.get("source_document_ids", [])),
                    created_at=datetime.now(timezone.utc),
                )
        except (ServiceUnavailable, DriverError):
            self._is_available = False
            return await self._fallback.get_entity(user_id, entity_id)

    async def get_entity_by_name(
        self, user_id: str, name: str, entity_type: Optional[str] = None
    ) -> Optional[EntityResponse]:
        driver = await self.get_driver()
        if not driver:
            return await self._fallback.get_entity_by_name(user_id, name, entity_type)

        norm_name = normalize_entity_name(name)
        cypher = """
        MATCH (n:Entity {user_id: $user_id})
        WHERE (n.normalized_name = $norm_name OR toLower(n.name) = toLower($raw_name) OR $raw_name IN n.aliases)
        """
        if entity_type and entity_type in ALLOWED_LABELS:
            cypher += f" AND n:{entity_type} "
        cypher += " RETURN n LIMIT 1"

        try:
            async with driver.session(database=self.database) as session:
                result = await session.run(cypher, {"user_id": user_id, "norm_name": norm_name, "raw_name": name.strip()})
                record = await result.single()
                if not record:
                    return None
                n = record["n"]
                return EntityResponse(
                    id=n["id"],
                    user_id=n["user_id"],
                    name=n["name"],
                    type=n["type"],
                    aliases=list(n.get("aliases", [])),
                    confidence=float(n.get("confidence", 1.0)),
                    description=n.get("description"),
                    properties={},
                    source_document_ids=list(n.get("source_document_ids", [])),
                    created_at=datetime.now(timezone.utc),
                )
        except (ServiceUnavailable, DriverError):
            self._is_available = False
            return await self._fallback.get_entity_by_name(user_id, name, entity_type)

    async def get_entity_relationships(
        self,
        user_id: str,
        entity_id: str,
        direction: str = "both",
        relationship_types: Optional[List[str]] = None,
        temporal_year: Optional[int] = None,
    ) -> List[RelationshipResponse]:
        driver = await self.get_driver()
        if not driver:
            return await self._fallback.get_entity_relationships(
                user_id, entity_id, direction, relationship_types, temporal_year
            )

        pattern = "-[r]-"
        if direction == "outbound":
            pattern = "-[r]->"
        elif direction == "inbound":
            pattern = "<-[r]-"

        cypher = f"""
        MATCH (src:Entity {{user_id: $user_id}}){pattern}(tgt:Entity {{user_id: $user_id}})
        WHERE (src.id = $entity_id OR tgt.id = $entity_id)
        """
        if temporal_year is not None:
            cypher += """
            AND (r.valid_from IS NULL OR r.valid_from <= $year)
            AND (r.valid_to IS NULL OR r.valid_to >= $year)
            """
        cypher += " RETURN r, src, tgt, type(r) AS rel_type LIMIT 100"

        try:
            async with driver.session(database=self.database) as session:
                result = await session.run(
                    cypher,
                    {"user_id": user_id, "entity_id": entity_id, "year": temporal_year},
                )
                records = await result.data()
                responses: List[RelationshipResponse] = []
                for rec in records:
                    r = rec["r"]
                    src = rec["src"]
                    tgt = rec["tgt"]
                    responses.append(
                        RelationshipResponse(
                            id=r["id"],
                            user_id=user_id,
                            source_entity_id=src["id"],
                            target_entity_id=tgt["id"],
                            relationship_type=rec["rel_type"],
                            confidence=float(r.get("confidence", 1.0)),
                            source_document_id=r.get("source_document_id"),
                            source_chunk_id=r.get("source_chunk_id"),
                            source_page=r.get("source_page"),
                            valid_from=r.get("valid_from"),
                            valid_to=r.get("valid_to"),
                            properties={},
                            source_entity_name=src["name"],
                            source_entity_type=src["type"],
                            target_entity_name=tgt["name"],
                            target_entity_type=tgt["type"],
                            created_at=datetime.now(timezone.utc),
                        )
                    )
                return responses
        except (ServiceUnavailable, DriverError):
            self._is_available = False
            return await self._fallback.get_entity_relationships(
                user_id, entity_id, direction, relationship_types, temporal_year
            )

    async def get_neighbors(
        self,
        user_id: str,
        entity_id: str,
        max_hops: int = 1,
        relationship_types: Optional[List[str]] = None,
        temporal_year: Optional[int] = None,
        limit: int = 50,
    ) -> GraphVisualizationResponse:
        driver = await self.get_driver()
        if not driver:
            return await self._fallback.get_neighbors(
                user_id, entity_id, max_hops, relationship_types, temporal_year, limit
            )

        hops = min(max(1, max_hops), settings.MAX_GRAPH_HOPS)
        cypher = f"""
        MATCH path = (root:Entity {{id: $entity_id, user_id: $user_id}})-[r*1..{hops}]-(neighbor:Entity {{user_id: $user_id}})
        UNWIND relationships(path) AS rel
        UNWIND nodes(path) AS node
        RETURN DISTINCT node, rel, type(rel) AS rel_type LIMIT $limit
        """

        try:
            async with driver.session(database=self.database) as session:
                result = await session.run(cypher, {"entity_id": entity_id, "user_id": user_id, "limit": limit})
                records = await result.data()

                node_map: Dict[str, GraphNode] = {}
                edge_map: Dict[str, GraphEdge] = {}

                for rec in records:
                    n = rec["node"]
                    rel = rec["rel"]
                    rel_type = rec["rel_type"]

                    if n["id"] not in node_map:
                        node_map[n["id"]] = GraphNode(
                            id=n["id"],
                            label=n["name"],
                            type=n["type"],
                            metadata={"confidence": n.get("confidence", 1.0), "aliases": n.get("aliases", [])},
                        )

                    edge_id = rel.get("id") or f"{rel.start_node['id']}-{rel_type}-{rel.end_node['id']}"
                    if edge_id not in edge_map:
                        edge_map[edge_id] = GraphEdge(
                            id=edge_id,
                            source=rel.start_node.get("id", ""),
                            target=rel.end_node.get("id", ""),
                            relationship=rel_type,
                            confidence=float(rel.get("confidence", 1.0)),
                            source_document=rel.get("source_document_id"),
                            valid_from=rel.get("valid_from"),
                            valid_to=rel.get("valid_to"),
                            metadata={},
                        )

                return GraphVisualizationResponse(nodes=list(node_map.values()), edges=list(edge_map.values()))
        except (ServiceUnavailable, DriverError):
            self._is_available = False
            return await self._fallback.get_neighbors(
                user_id, entity_id, max_hops, relationship_types, temporal_year, limit
            )

    async def search_entities(
        self,
        user_id: str,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[EntityResponse]:
        driver = await self.get_driver()
        if not driver:
            return await self._fallback.search_entities(user_id, query, entity_types, limit)

        norm = normalize_entity_name(query)
        cypher = """
        MATCH (n:Entity {user_id: $user_id})
        WHERE toLower(n.name) CONTAINS toLower($q)
           OR n.normalized_name CONTAINS $norm
           OR any(a IN n.aliases WHERE toLower(a) CONTAINS toLower($q))
        """
        if entity_types:
            valid_types = [t for t in entity_types if t in ALLOWED_LABELS]
            if valid_types:
                labels_clause = " OR ".join([f"n:{t}" for t in valid_types])
                cypher += f" AND ({labels_clause}) "

        cypher += " RETURN n LIMIT $limit"

        try:
            async with driver.session(database=self.database) as session:
                result = await session.run(cypher, {"user_id": user_id, "q": query.strip(), "norm": norm, "limit": limit})
                records = await result.data()
                return [
                    EntityResponse(
                        id=r["n"]["id"],
                        user_id=r["n"]["user_id"],
                        name=r["n"]["name"],
                        type=r["n"]["type"],
                        aliases=list(r["n"].get("aliases", [])),
                        confidence=float(r["n"].get("confidence", 1.0)),
                        description=r["n"].get("description"),
                        properties={},
                        source_document_ids=list(r["n"].get("source_document_ids", [])),
                        created_at=datetime.now(timezone.utc),
                    )
                    for r in records
                ]
        except (ServiceUnavailable, DriverError):
            self._is_available = False
            return await self._fallback.search_entities(user_id, query, entity_types, limit)

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
        driver = await self.get_driver()
        if not driver:
            return await self._fallback.find_paths(
                user_id, start_entity_id, end_entity_id, max_hops, relationship_types, temporal_year, limit
            )

        hops = min(max(1, max_hops), settings.MAX_GRAPH_HOPS)
        if end_entity_id:
            cypher = f"""
            MATCH path = (src:Entity {{id: $start_id, user_id: $user_id}})-[r*1..{hops}]-(tgt:Entity {{id: $end_id, user_id: $user_id}})
            RETURN path LIMIT $limit
            """
            params = {"start_id": start_entity_id, "end_id": end_entity_id, "user_id": user_id, "limit": limit}
        else:
            cypher = f"""
            MATCH path = (src:Entity {{id: $start_id, user_id: $user_id}})-[r*1..{hops}]-(tgt:Entity {{user_id: $user_id}})
            RETURN path LIMIT $limit
            """
            params = {"start_id": start_entity_id, "user_id": user_id, "limit": limit}


        try:
            async with driver.session(database=self.database) as session:
                result = await session.run(cypher, params)
                records = await result.data()
                paths = []
                for rec in records:
                    p = rec["path"]
                    paths.append({
                        "length": len(p.relationships),
                        "nodes": [n["name"] for n in p.nodes],
                        "node_types": [n["type"] for n in p.nodes],
                        "relationships": [type(r).__name__ for r in p.relationships],
                    })
                return paths
        except (ServiceUnavailable, DriverError):
            self._is_available = False
            return await self._fallback.find_paths(
                user_id, start_entity_id, end_entity_id, max_hops, relationship_types, temporal_year, limit
            )

    async def get_full_graph(
        self, user_id: str, limit: int = 150
    ) -> GraphVisualizationResponse:
        driver = await self.get_driver()
        if not driver:
            return await self._fallback.get_full_graph(user_id, limit)

        cypher = """
        MATCH (n:Entity {user_id: $user_id})
        OPTIONAL MATCH (n)-[r]->(m:Entity {user_id: $user_id})
        RETURN n, r, m, type(r) AS rel_type LIMIT $limit
        """
        try:
            async with driver.session(database=self.database) as session:
                result = await session.run(cypher, {"user_id": user_id, "limit": limit})
                records = await result.data()

                node_map: Dict[str, GraphNode] = {}
                edges: List[GraphEdge] = []

                for rec in records:
                    n = rec["n"]
                    if n["id"] not in node_map:
                        node_map[n["id"]] = GraphNode(
                            id=n["id"],
                            label=n["name"],
                            type=n["type"],
                            metadata={"confidence": n.get("confidence", 1.0), "aliases": n.get("aliases", [])},
                        )

                    if rec.get("r") and rec.get("m"):
                        m = rec["m"]
                        if m["id"] not in node_map:
                            node_map[m["id"]] = GraphNode(
                                id=m["id"],
                                label=m["name"],
                                type=m["type"],
                                metadata={"confidence": n.get("confidence", 1.0), "aliases": n.get("aliases", [])},
                            )
                        r = rec["r"]
                        edge_id = r.get("id") or f"{n['id']}-{rec['rel_type']}-{m['id']}"
                        edges.append(
                            GraphEdge(
                                id=edge_id,
                                source=n["id"],
                                target=m["id"],
                                relationship=rec["rel_type"],
                                confidence=float(r.get("confidence", 1.0)),
                                source_document=r.get("source_document_id"),
                                valid_from=r.get("valid_from"),
                                valid_to=r.get("valid_to"),
                                metadata={},
                            )
                        )

                return GraphVisualizationResponse(nodes=list(node_map.values()), edges=edges)
        except (ServiceUnavailable, DriverError):
            self._is_available = False
            return await self._fallback.get_full_graph(user_id, limit)

    async def delete_document_graph_data(self, user_id: str, document_id: str) -> None:
        driver = await self.get_driver()
        if not driver:
            return await self._fallback.delete_document_graph_data(user_id, document_id)

        cypher = """
        MATCH ()-[r {user_id: $user_id, source_document_id: $doc_id}]->()
        DELETE r
        """
        try:
            async with driver.session(database=self.database) as session:
                await session.run(cypher, {"user_id": user_id, "doc_id": document_id})
        except (ServiceUnavailable, DriverError):
            self._is_available = False
            await self._fallback.delete_document_graph_data(user_id, document_id)
