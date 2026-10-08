import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent_service import AgentRAGService
from app.agent.workflow import agent_workflow
from app.models.user import User
from app.schemas.graph import EntityCreate, RelationshipCreate
from app.services.graph_service import GraphService


@pytest.mark.asyncio
async def test_agent_workflow_structure():
    # Verify LangGraph compiled workflow has all required nodes
    nodes = agent_workflow.nodes
    expected_nodes = [
        "query_analyzer",
        "entity_resolver",
        "retrieval_planner",
        "retriever",
        "evidence_evaluator",
        "research_agent",
        "answer_generator",
        "fact_checker",
        "citation_validator",
    ]
    for node_name in expected_nodes:
        assert node_name in nodes


@pytest.mark.asyncio
async def test_agentic_multi_hop_query(db_session: AsyncSession, test_user: User):
    agent_svc = AgentRAGService(db_session)
    user_id = test_user.id

    # 1. Setup multi-hop data in Knowledge Graph
    graph_service = GraphService()
    p_google = await graph_service.store.upsert_entity(
        user_id, EntityCreate(name="Google", type="Company", source_document_id="doc_sec_100")
    )
    p_researcher = await graph_service.store.upsert_entity(
        user_id, EntityCreate(name="Geoffrey Hinton", type="Person", source_document_id="doc_sec_100")
    )
    p_startup = await graph_service.store.upsert_entity(
        user_id, EntityCreate(name="DNNresearch", type="Startup", source_document_id="doc_sec_100")
    )

    await graph_service.store.upsert_relationship(
        user_id,
        RelationshipCreate(
            source_entity_id=p_researcher.id,
            target_entity_id=p_google.id,
            relationship_type="WORKED_AT",
            source_document_id="doc_sec_100",
            valid_from=2013,
            valid_to=2023,
        ),
    )

    await graph_service.store.upsert_relationship(
        user_id,
        RelationshipCreate(
            source_entity_id=p_researcher.id,
            target_entity_id=p_startup.id,
            relationship_type="FOUNDED",
            source_document_id="doc_sec_100",
            valid_from=2012,
        ),
    )

    # 2. Execute multi-hop query
    response = await agent_svc.execute(
        question="Which startups were founded by former Google employees who worked there?",
        user_id=user_id,
    )

    assert response.retrieval_mode == "agentic"
    assert response.answer is not None
    assert len(response.evidence) >= 1
    assert any("DNNresearch" in e.content for e in response.evidence)


@pytest.mark.asyncio
async def test_agentic_insufficient_evidence(db_session: AsyncSession, test_user: User):
    agent_svc = AgentRAGService(db_session)
    user_id = test_user.id

    # Unrecorded entity and future speculation
    response = await agent_svc.execute(
        question="Which company will acquire FutureAI Corp in 2038?",
        user_id=user_id,
    )

    assert response.retrieval_mode == "agentic"
    assert "insufficient evidence" in response.answer.lower()


@pytest.mark.asyncio
async def test_agent_api_endpoints(client: AsyncClient, test_user: User, auth_headers: dict):
    # 1. Test POST /api/v1/query with retrieval_mode="agentic"
    payload1 = {
        "question": "What are the key market developments for Microsoft in enterprise AI?",
        "retrieval_mode": "agentic",
    }
    resp1 = await client.post("/api/v1/query", json=payload1, headers=auth_headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["retrieval_mode"] == "agentic"
    assert "answer" in data1

    # 2. Test dedicated POST /api/v1/query/agent
    payload2 = {
        "question": "Who founded Nova AI and which firm acquired it?",
    }
    resp2 = await client.post("/api/v1/query/agent", json=payload2, headers=auth_headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["retrieval_mode"] == "agentic"
    assert "answer" in data2
