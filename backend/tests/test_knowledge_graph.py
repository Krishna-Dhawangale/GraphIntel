import pytest
from httpx import AsyncClient

from app.models.user import User
from app.providers.graph_store.in_memory_store import InMemoryGraphStore
from app.schemas.graph import (
    EntityCreate,
    NodeType,
    RelationshipCreate,
    RelationshipType,
)
from app.services.entity_extractor import RuleBasedEntityExtractor
from app.services.entity_resolver import EntityResolver
from app.services.graph_service import GraphService


@pytest.mark.asyncio
async def test_entity_extractor_rules():
    extractor = RuleBasedEntityExtractor()
    text = (
        "Satya Nadella served as CEO of Microsoft in 2024. "
        "Microsoft acquired XYZ AI in 2025. "
        "XYZ AI was founded by former Google researcher Alice Smith."
    )
    entities, rels = await extractor.extract(
        text=text,
        document_id="doc_123",
        chunk_id="chunk_456",
        page_number=1,
    )

    entity_names = {e.name for e in entities}
    assert "Microsoft" in entity_names
    assert "Satya Nadella" in entity_names or any("Nadella" in e.name for e in entities)
    assert "XYZ AI" in entity_names

    # Verify relationships have source evidence
    assert len(rels) >= 2
    for r in rels:
        assert r.source_document_id == "doc_123"
        assert r.source_chunk_id == "chunk_456"
        assert r.source_page == 1
        assert r.confidence > 0.8


@pytest.mark.asyncio
async def test_entity_resolver_aliases_and_suffixes():
    resolver = EntityResolver()
    existing = [
        {"name": "Microsoft", "type": "Company", "aliases": ["MSFT"]},
        {"name": "Google", "type": "Company", "aliases": ["Alphabet"]},
    ]

    # Test alias resolution
    canonical, aliases, conf = resolver.resolve("MSFT", "Company", existing)
    assert canonical == "Microsoft"
    assert conf >= 0.95

    # Test suffix stripping
    canonical, aliases, conf = resolver.resolve("Microsoft Corp.", "Company", existing)
    assert canonical == "Microsoft"

    # Test distinct entity not falsely merged
    canonical, aliases, conf = resolver.resolve("MicroStrategy Inc.", "Company", existing)
    assert canonical == "MicroStrategy Inc."


@pytest.mark.asyncio
async def test_graph_store_idempotency():
    store = InMemoryGraphStore()
    user_id = "user_test_1"

    # Upsert entity twice
    ent1 = EntityCreate(name="Microsoft", type="Company", confidence=0.9, source_document_id="doc_1")
    res1 = await store.upsert_entity(user_id, ent1)

    ent2 = EntityCreate(name="Microsoft", type="Company", confidence=0.95, source_document_id="doc_2")
    res2 = await store.upsert_entity(user_id, ent2)

    assert res1.id == res2.id
    assert res2.confidence == 0.95
    assert "doc_1" in res2.source_document_ids
    assert "doc_2" in res2.source_document_ids

    # Search should return only 1 entity
    results = await store.search_entities(user_id, "Microsoft")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_temporal_graph_relationships():
    store = InMemoryGraphStore()
    user_id = "user_test_2"

    person = await store.upsert_entity(user_id, EntityCreate(name="John Doe", type="Person", source_document_id="doc_1"))
    comp_a = await store.upsert_entity(user_id, EntityCreate(name="Company A", type="Company", source_document_id="doc_1"))
    comp_b = await store.upsert_entity(user_id, EntityCreate(name="Company B", type="Company", source_document_id="doc_1"))

    # CEO of Company A from 2020 to 2023
    await store.upsert_relationship(
        user_id,
        RelationshipCreate(
            source_entity_id=person.id,
            target_entity_id=comp_a.id,
            relationship_type="CEO_OF",
            valid_from=2020,
            valid_to=2023,
            source_document_id="doc_1",
        ),
    )

    # CEO of Company B from 2024 to 2026
    await store.upsert_relationship(
        user_id,
        RelationshipCreate(
            source_entity_id=person.id,
            target_entity_id=comp_b.id,
            relationship_type="CEO_OF",
            valid_from=2024,
            valid_to=2026,
            source_document_id="doc_1",
        ),
    )

    # Query for 2022 -> should only return Company A
    rels_2022 = await store.get_entity_relationships(user_id, person.id, temporal_year=2022)
    assert len(rels_2022) == 1
    assert rels_2022[0].target_entity_name == "Company A"

    # Query for 2025 -> should only return Company B
    rels_2025 = await store.get_entity_relationships(user_id, person.id, temporal_year=2025)
    assert len(rels_2025) == 1
    assert rels_2025[0].target_entity_name == "Company B"


@pytest.mark.asyncio
async def test_graph_apis(client: AsyncClient, test_user: User, auth_headers: dict):
    # 1. Sync graph data via graph service
    graph_service = GraphService()
    user_id = test_user.id


    await graph_service.sync_chunk_to_graph(
        user_id=user_id,
        document_id="doc_api_test",
        chunk_id="chunk_api_1",
        text="Alpha Corp acquired Beta AI in 2024. Alice was the CEO of Alpha Corp in 2024.",
        page_number=1,
    )

    # 2. Test search API
    search_resp = await client.get("/api/v1/graph/search?q=Alpha", headers=auth_headers)
    assert search_resp.status_code == 200
    entities = search_resp.json()
    assert len(entities) >= 1
    alpha_id = entities[0]["id"]

    # 3. Test entity lookup API
    ent_resp = await client.get(f"/api/v1/entities/{alpha_id}", headers=auth_headers)
    assert ent_resp.status_code == 200
    assert ent_resp.json()["id"] == alpha_id

    # 4. Test relationships API
    rels_resp = await client.get(f"/api/v1/entities/{alpha_id}/relationships", headers=auth_headers)
    assert rels_resp.status_code == 200
    rels = rels_resp.json()
    assert len(rels) >= 1

    # 5. Test graph detail API
    detail_resp = await client.get(f"/api/v1/graph/entity/{alpha_id}", headers=auth_headers)
    assert detail_resp.status_code == 200
    assert "entity" in detail_resp.json()
    assert "relationships" in detail_resp.json()

    # 6. Test neighbors API
    neighbors_resp = await client.get(f"/api/v1/graph/neighbors/{alpha_id}?max_hops=2", headers=auth_headers)
    assert neighbors_resp.status_code == 200
    vis = neighbors_resp.json()
    assert "nodes" in vis
    assert "edges" in vis

    # 7. Test full graph visualization API
    vis_resp = await client.get("/api/v1/graph/visualization", headers=auth_headers)
    assert vis_resp.status_code == 200
    full_vis = vis_resp.json()
    assert len(full_vis["nodes"]) >= 2
    assert len(full_vis["edges"]) >= 1
