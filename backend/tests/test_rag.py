import io

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rag_query_and_citations_pipeline(
    client: AsyncClient,
    auth_headers: dict,
    other_auth_headers: dict,
):
    # 1. Ingest document with market intelligence data
    content = (
        "Enterprise SaaS Market Intelligence Report 2026.\n\n"
        "Total addressable market reached $450 billion in fiscal year 2025. "
        "Top competitors include CloudCorp and DataDynamics. "
        "CloudCorp achieved 34 percent market share while DataDynamics captured 22 percent."
    )
    files = {"file": ("saas_market_report.txt", io.BytesIO(content.encode("utf-8")), "text/plain")}
    upload_res = await client.post("/api/v1/documents", files=files, headers=auth_headers)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 2. Query the document
    query_payload = {
        "question": "What was the total addressable market and market share of CloudCorp?",
        "top_k": 3,
        "document_ids": [doc_id],
    }
    query_res = await client.post("/api/v1/query", json=query_payload, headers=auth_headers)
    assert query_res.status_code == 200
    res_data = query_res.json()

    assert "answer" in res_data
    assert "sources" in res_data
    assert len(res_data["sources"]) > 0
    assert "retrieved_chunks" in res_data
    assert len(res_data["retrieved_chunks"]) > 0

    # Verify citation attributes
    first_source = res_data["sources"][0]
    assert first_source["document_id"] == doc_id
    assert first_source["filename"] == "saas_market_report.txt"
    assert first_source["citation_order"] == 1

    # Verify metadata timings
    meta = res_data["metadata"]
    assert "retrieval_time_ms" in meta
    assert "llm_time_ms" in meta
    assert meta["chunks_retrieved"] >= 1

    # 3. Query history
    history_res = await client.get("/api/v1/query/history", headers=auth_headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) >= 1
    assert history[0]["question"] == query_payload["question"]

    # 4. User isolation: other user asks the same question, should NOT retrieve user 1's document
    other_query_res = await client.post(
        "/api/v1/query", json=query_payload, headers=other_auth_headers
    )
    assert other_query_res.status_code == 200
    other_data = other_query_res.json()
    assert len(other_data["sources"]) == 0
    assert len(other_data["retrieved_chunks"]) == 0
    assert "insufficient evidence" in other_data["answer"].lower()
