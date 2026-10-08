import io

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_document_lifecycle_and_ownership(
    client: AsyncClient,
    auth_headers: dict,
    other_auth_headers: dict,
):
    # 1. Upload a valid document
    file_content = (
        b"GraphIntel Q3 Financial Briefing.\nNet revenue increased by 25 percent to $120 million."
    )
    files = {"file": ("q3_briefing.txt", io.BytesIO(file_content), "text/plain")}
    data = {"title": "Q3 Briefing"}

    upload_res = await client.post(
        "/api/v1/documents", files=files, data=data, headers=auth_headers
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    assert doc_data["title"] == "Q3 Briefing"
    assert doc_data["status"] == "COMPLETED"

    # 2. List user's documents
    list_res = await client.get("/api/v1/documents", headers=auth_headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(d["id"] == doc_id for d in list_data["items"])

    # 3. Get document details
    get_res = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["chunks_count"] >= 1

    # 4. Get chunks
    chunks_res = await client.get(f"/api/v1/documents/{doc_id}/chunks", headers=auth_headers)
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert len(chunks) >= 1
    assert "GraphIntel Q3 Financial" in chunks[0]["text"]

    # 5. Status endpoint
    status_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "COMPLETED"

    # 6. Authorization check: Other user CANNOT access this document
    forbidden_res = await client.get(f"/api/v1/documents/{doc_id}", headers=other_auth_headers)
    assert forbidden_res.status_code == 403

    # 7. Delete document
    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert del_res.status_code == 204

    # 8. Verify document is gone
    not_found_res = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert not_found_res.status_code == 404
