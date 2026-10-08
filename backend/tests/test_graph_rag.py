import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.graph import EntityCreate, RelationshipCreate
from app.services.graph_service import GraphService
from app.services.rag_service import RAGService


@pytest.mark.asyncio
async def test_graphrag_retrieval_modes(db_session: AsyncSession, test_user: User):
    rag_service = RAGService(db_session)
    user_id = test_user.id

    # 1. Populate knowledge graph with multi-tier market data
    graph_service = GraphService()
    p_google = await graph_service.store.upsert_entity(
        user_id, EntityCreate(name="Google", type="Company", source_document_id="doc_sec_1")
    )
    p_alice = await graph_service.store.upsert_entity(
        user_id, EntityCreate(name="Alice Smith", type="Person", source_document_id="doc_sec_1")
    )
    p_startup = await graph_service.store.upsert_entity(
        user_id, EntityCreate(name="Nova AI", type="Startup", source_document_id="doc_sec_1")
    )
    p_acquirer = await graph_service.store.upsert_entity(
        user_id, EntityCreate(name="Microsoft", type="Company", source_document_id="doc_sec_1")
    )

    # Alice WORKED_AT Google
    await graph_service.store.upsert_relationship(
        user_id,
        RelationshipCreate(
            source_entity_id=p_alice.id,
            target_entity_id=p_google.id,
            relationship_type="WORKED_AT",
            source_document_id="doc_sec_1",
            valid_from=2018,
            valid_to=2022,
        ),
    )

    # Alice FOUNDED Nova AI
    await graph_service.store.upsert_relationship(
        user_id,
        RelationshipCreate(
            source_entity_id=p_alice.id,
            target_entity_id=p_startup.id,
            relationship_type="FOUNDED",
            source_document_id="doc_sec_1",
            valid_from=2023,
        ),
    )

    # Microsoft ACQUIRED Nova AI
    await graph_service.store.upsert_relationship(
        user_id,
        RelationshipCreate(
            source_entity_id=p_acquirer.id,
            target_entity_id=p_startup.id,
            relationship_type="ACQUIRED",
            source_document_id="doc_sec_1",
            valid_from=2025,
            valid_to=2025,
        ),
    )

    # 2. Test Graph Mode: Entity relationship query
    res_graph = await rag_service.answer_query(
        question="Which company acquired Nova AI?",
        user_id=user_id,
        retrieval_mode="graph",
    )
    assert res_graph.retrieval_mode == "graph"
    assert len(res_graph.evidence) >= 1
    assert any("Microsoft" in e.content for e in res_graph.evidence)

    # 3. Test Hybrid Mode: Multi-hop question
    res_hybrid = await rag_service.answer_query(
        question="Which companies acquired startups founded by former Google employees?",
        user_id=user_id,
        retrieval_mode="hybrid",
        max_graph_hops=3,
    )
    assert res_hybrid.retrieval_mode == "hybrid"
    assert len(res_hybrid.evidence) >= 1

    # 4. Test Temporal Query
    res_temporal = await rag_service.answer_query(
        question="Where did Alice Smith work in 2020?",
        user_id=user_id,
        retrieval_mode="hybrid",
        temporal_year=2020,
    )
    assert res_temporal.retrieval_mode == "hybrid"
    assert any("Google" in e.content for e in res_temporal.evidence)

    # 5. Test Insufficient Evidence: speculative future question without evidence
    res_speculative = await rag_service.answer_query(
        question="Which company will acquire QuantumCorp in 2035?",
        user_id=user_id,
        retrieval_mode="hybrid",
    )
    assert "insufficient evidence" in res_speculative.answer.lower()


@pytest.mark.asyncio
async def test_graphrag_api_endpoint(client: AsyncClient, test_user: User, auth_headers: dict):
    # Call POST /api/v1/query with hybrid retrieval mode
    payload = {
        "question": "What is the strategic acquisition history of Microsoft?",
        "retrieval_mode": "hybrid",
        "top_k": 5,
        "max_graph_hops": 3,
    }
    response = await client.post("/api/v1/query", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "retrieval_mode" in data
    assert data["retrieval_mode"] == "hybrid"
    assert "metadata" in data
    assert "graph_retrieval_time_ms" in data["metadata"]
