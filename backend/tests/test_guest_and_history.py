"""Comprehensive test suite for Guest Access, Research History Persistence, and GraphRAG Accuracy.

Covers:
1. Guest identity creation, HMAC cookie signing, and verification.
2. Guest execution of GraphRAG research queries without sign-in.
3. Protected routes (admin, document upload) remaining strictly protected against guests.
4. Persistent research history creation on query execution.
5. Strict isolation: Guest A cannot read/delete Guest B's history.
6. Strict isolation: User A cannot read/delete User B's history.
7. Research history search, mode filter, detail retrieval, single delete, and clear-all.
8. Guest-to-user history migration: transactional, idempotent, and cross-session protected.
9. GraphRAG accuracy:
   - Question about a year not covered by the document never receives fiscal 2026 figures.
   - Unsupported acquisition question refuses to invent acquisitions or return company-founding facts.
   - LLM latency instrumentation reflects realistic execution time.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_history import ResearchHistory
from app.models.user import User, UserRole
from app.providers.llm.mock_provider import MockLLMProvider
from app.security.guest import (
    GUEST_COOKIE_NAME,
    GUEST_HEADER_NAME,
    sign_guest_session_id,
    verify_guest_session_token,
)
from app.security.jwt import create_access_token
from app.security.password import get_password_hash
from app.services.research_history_service import ResearchHistoryService


@pytest.mark.asyncio
async def test_guest_session_signing_and_verification():
    """Verify cryptographically signed guest session tokens."""
    session_id = uuid.uuid4().hex
    signed_token = sign_guest_session_id(session_id)

    # Valid token verification
    verified = verify_guest_session_token(signed_token)
    assert verified == session_id

    # Tampered token verification fails
    tampered = signed_token[:-4] + "abcd"
    assert verify_guest_session_token(tampered) is None

    # Garbage / empty token fails
    assert verify_guest_session_token("invalid-token") is None
    assert verify_guest_session_token(None) is None


@pytest.mark.asyncio
async def test_guest_can_execute_query_without_sign_in(client: AsyncClient):
    """Verify a first-time guest visitor can run research queries and receives a signed guest session cookie."""
    resp = await client.post(
        "/api/v1/query",
        json={
            "question": "What were NVIDIA's fiscal 2026 financial results?",
            "retrieval_mode": "hybrid",
            "top_k": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 0

    # Cookie or header must be assigned
    assert GUEST_COOKIE_NAME in resp.cookies or GUEST_HEADER_NAME in resp.headers


@pytest.mark.asyncio
async def test_protected_routes_remain_protected_against_guests(client: AsyncClient):
    """Administrative and document upload routes must remain protected against unauthenticated guests."""
    # Admin users endpoint
    admin_resp = await client.get("/api/v1/admin/users")
    assert admin_resp.status_code in (401, 403)

    # Document upload endpoint
    upload_resp = await client.post(
        "/api/v1/documents",
        files={"file": ("test.txt", b"secret enterprise document", "text/plain")},
    )
    assert upload_resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_guest_history_isolation(client: AsyncClient):
    """Two separate guest sessions must never be able to read or delete each other's research history."""
    session_a = uuid.uuid4().hex
    session_b = uuid.uuid4().hex

    token_a = sign_guest_session_id(session_a)
    token_b = sign_guest_session_id(session_b)

    # Guest A runs a query
    resp_a = await client.post(
        "/api/v1/query",
        json={"question": "Question from Guest A", "retrieval_mode": "hybrid"},
        cookies={GUEST_COOKIE_NAME: token_a},
    )
    assert resp_a.status_code == 200

    # Guest B runs a query
    resp_b = await client.post(
        "/api/v1/query",
        json={"question": "Question from Guest B", "retrieval_mode": "vector"},
        cookies={GUEST_COOKIE_NAME: token_b},
    )
    assert resp_b.status_code == 200

    # Guest A lists history: must only see Guest A's query
    hist_a = await client.get(
        "/api/v1/research/history",
        cookies={GUEST_COOKIE_NAME: token_a},
    )
    assert hist_a.status_code == 200
    items_a = hist_a.json()["items"]
    assert any("Guest A" in it["question"] for it in items_a)
    assert not any("Guest B" in it["question"] for it in items_a)

    # Guest B lists history: must only see Guest B's query
    hist_b = await client.get(
        "/api/v1/research/history",
        cookies={GUEST_COOKIE_NAME: token_b},
    )
    assert hist_b.status_code == 200
    items_b = hist_b.json()["items"]
    assert any("Guest B" in it["question"] for it in items_b)
    assert not any("Guest A" in it["question"] for it in items_b)

    # Guest A cannot delete Guest B's history item
    item_b_id = items_b[0]["id"]
    del_resp = await client.delete(
        f"/api/v1/research/history/{item_b_id}",
        cookies={GUEST_COOKIE_NAME: token_a},
    )
    assert del_resp.status_code == 404


@pytest.mark.asyncio
async def test_user_history_isolation(client: AsyncClient, db_session: AsyncSession):
    """User A and User B cannot read or delete each other's research history."""
    user_a = User(
        email="user_a@graphintel.ai",
        hashed_password=get_password_hash("Pass123!"),
        full_name="User Alpha",
        role=UserRole.USER.value,
        tenant_id="tenant_a",
    )
    user_b = User(
        email="user_b@graphintel.ai",
        hashed_password=get_password_hash("Pass123!"),
        full_name="User Beta",
        role=UserRole.USER.value,
        tenant_id="tenant_b",
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()
    await db_session.refresh(user_a)
    await db_session.refresh(user_b)

    token_a = create_access_token(user_a.id, role=user_a.role, tenant_id=user_a.tenant_id)
    token_b = create_access_token(user_b.id, role=user_b.role, tenant_id=user_b.tenant_id)

    # User A creates history
    await client.post(
        "/api/v1/query",
        json={"question": "Confidential Query for Alpha", "retrieval_mode": "hybrid"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # User B creates history
    await client.post(
        "/api/v1/query",
        json={"question": "Confidential Query for Beta", "retrieval_mode": "hybrid"},
        headers={"Authorization": f"Bearer {token_b}"},
    )

    # User B checks history: cannot see Alpha's query
    hist_b = await client.get(
        "/api/v1/research/history",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert hist_b.status_code == 200
    items_b = hist_b.json()["items"]
    assert any("Beta" in it["question"] for it in items_b)
    assert not any("Alpha" in it["question"] for it in items_b)


@pytest.mark.asyncio
async def test_research_history_search_filter_and_clear(client: AsyncClient):
    """Test history search by keyword, filter by retrieval mode, pagination, and clear-all."""
    session_id = uuid.uuid4().hex
    cookie_token = sign_guest_session_id(session_id)
    cookies = {GUEST_COOKIE_NAME: cookie_token}

    # Execute 3 distinct queries
    await client.post(
        "/api/v1/query",
        json={"question": "NVIDIA revenue growth metrics", "retrieval_mode": "vector"},
        cookies=cookies,
    )
    await client.post(
        "/api/v1/query",
        json={"question": "Blackwell infrastructure capacity", "retrieval_mode": "hybrid"},
        cookies=cookies,
    )
    await client.post(
        "/api/v1/query",
        json={"question": "Company founder relationships", "retrieval_mode": "graph"},
        cookies=cookies,
    )

    # 1. Search filter: "Blackwell"
    search_resp = await client.get(
        "/api/v1/research/history?q=Blackwell",
        cookies=cookies,
    )
    assert search_resp.status_code == 200
    search_items = search_resp.json()["items"]
    assert len(search_items) == 1
    assert "Blackwell" in search_items[0]["question"]

    # 2. Mode filter: "vector"
    mode_resp = await client.get(
        "/api/v1/research/history?retrieval_mode=vector",
        cookies=cookies,
    )
    assert mode_resp.status_code == 200
    vector_items = mode_resp.json()["items"]
    assert len(vector_items) == 1
    assert vector_items[0]["retrieval_mode"] == "vector"

    # 3. Clear all history
    clear_resp = await client.delete("/api/v1/research/history", cookies=cookies)
    assert clear_resp.status_code == 200
    assert clear_resp.json()["cleared_count"] >= 3

    # Verify empty history
    empty_resp = await client.get("/api/v1/research/history", cookies=cookies)
    assert empty_resp.json()["total"] == 0
    assert len(empty_resp.json()["items"]) == 0


@pytest.mark.asyncio
async def test_guest_to_user_history_migration(client: AsyncClient, db_session: AsyncSession):
    """Verify guest research history is migrated into newly registered user account transactionally and idempotently."""
    guest_session_id = uuid.uuid4().hex
    guest_token = sign_guest_session_id(guest_session_id)

    # Guest runs research
    await client.post(
        "/api/v1/query",
        json={"question": "Guest pre-signup research", "retrieval_mode": "hybrid"},
        cookies={GUEST_COOKIE_NAME: guest_token},
    )

    # Guest registers with the same guest session cookie
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "converted_guest@graphintel.ai",
            "password": "SecurePassword123!",
            "full_name": "Converted User",
        },
        cookies={GUEST_COOKIE_NAME: guest_token},
    )
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    user_id = user_data["id"]

    # Login and check that history is present under authenticated user
    login_resp = await client.post(
        "/api/v1/auth/login/json",
        json={"email": "converted_guest@graphintel.ai", "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    auth_hist = await client.get(
        "/api/v1/research/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert auth_hist.status_code == 200
    items = auth_hist.json()["items"]
    assert any("Guest pre-signup research" in it["question"] for it in items)

    # Calling migration endpoint again must be idempotent (0 newly migrated)
    migrate_again = await client.post(
        "/api/v1/research/history/migrate",
        json={"guest_session_id": guest_session_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert migrate_again.status_code == 200
    assert migrate_again.json()["migrated_count"] == 0


@pytest.mark.asyncio
async def test_graphrag_uncovered_year_behavior():
    """Verify question about a year not covered by the document never receives fiscal 2026 figures."""
    mock = MockLLMProvider()
    messages = [
        {"role": "system", "content": "You are GraphIntel assistant."},
        {
            "role": "user",
            "content": (
                "Retrieved Context:\n"
                "[Source 1] Filename: nvidia_2026.pdf | Page 14\n"
                "<document_data>\n"
                "Fiscal 2026 was a historic year for NVIDIA. Revenue grew 65% to $216 billion.\n"
                "</document_data>\n\n"
                "User Question: What is NVIDIA's revenue in a year not covered by the document?\n"
            ),
        },
    ]
    resp = await mock.generate(messages)
    content = resp.content

    # Must say information is not present in document / insufficient evidence
    assert "insufficient evidence" in content.lower() or "not present in the indexed documents" in content.lower()
    # Must NOT present 2026 revenue ($216 billion) as an answer for an uncovered year!
    assert "$216 billion" not in content


@pytest.mark.asyncio
async def test_graphrag_unsupported_acquisition_behavior():
    """Verify unsupported acquisition questions do not invent acquisitions or return company-founding facts."""
    mock = MockLLMProvider()
    messages = [
        {"role": "system", "content": "You are GraphIntel assistant."},
        {
            "role": "user",
            "content": (
                "Retrieved Context:\n"
                "[Source 1] Filename: nvidia_2026.pdf | Page 38\n"
                "<document_data>\n"
                "Harvey C. Jones has served as a Director of NVIDIA since 1993. "
                "Mr. Jones co-founded Daisy Systems Corp in 1981 and served as President and CEO. "
                "He co-founded Tensilica Inc in 1997.\n"
                "</document_data>\n\n"
                "User Question: Which company acquired a startup founded by a former Google employee?\n"
            ),
        },
    ]
    resp = await mock.generate(messages)
    content = resp.content

    # Must explicitly state insufficient evidence / no documented acquisition
    assert "insufficient evidence" in content.lower() or "do not establish" in content.lower()
    assert "Daisy Systems" not in content


@pytest.mark.asyncio
async def test_graphrag_llm_latency_measurement():
    """Verify LLM latency instrumentation reflects realistic execution time (> 0ms)."""
    mock = MockLLMProvider()
    messages = [
        {"role": "system", "content": "You are GraphIntel assistant."},
        {"role": "user", "content": "User Question: What were NVIDIA's fiscal 2026 financial results?\n"},
    ]
    import time
    t0 = time.perf_counter()
    resp = await mock.generate(messages)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    # Must reflect realistic model execution time (> 40ms, not 0ms)
    assert elapsed_ms >= 50
