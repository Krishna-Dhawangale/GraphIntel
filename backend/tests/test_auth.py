import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    # 1. Register new user
    register_payload = {
        "email": "newanalyst@marketintelligence.com",
        "password": "StrongPassword2026!",
        "full_name": "Market Researcher",
    }
    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == register_payload["email"]
    assert "id" in user_data
    assert "hashed_password" not in user_data

    # 2. Duplicate registration should fail
    dup_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert dup_res.status_code == 400
    assert "EMAIL_EXISTS" in dup_res.json()["error"]["code"]

    # 3. Login with JSON
    login_res = await client.post(
        "/api/v1/auth/login/json",
        json={"email": register_payload["email"], "password": register_payload["password"]},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 4. Access protected /me endpoint
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == register_payload["email"]


@pytest.mark.asyncio
async def test_invalid_login(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/login/json",
        json={"email": "nonexistent@user.com", "password": "wrongpassword"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_google_auth_config(client: AsyncClient):
    res = await client.get("/api/v1/auth/google/config")
    assert res.status_code == 200
    data = res.json()
    assert "client_id" in data
    assert "enabled" in data


@pytest.mark.asyncio
async def test_google_auth_missing_credential(client: AsyncClient):
    res = await client.post("/api/v1/auth/google", json={})
    assert res.status_code == 400
    assert "MISSING_GOOGLE_CREDENTIAL" in res.json()["error"]["code"]


@pytest.mark.asyncio
async def test_google_auth_success_and_jwt_generation(client: AsyncClient, monkeypatch):
    from app.api.v1 import auth

    # Mock Google ID token verification
    async def mock_verify_google_id_token(token: str):
        return {
            "email": "googleresearcher@example.com",
            "google_id": "google_1234567890",
            "full_name": "Google Researcher",
            "avatar_url": "https://example.com/avatar.png",
            "email_verified": True,
        }

    monkeypatch.setattr(auth, "verify_google_id_token", mock_verify_google_id_token)

    # 1. Login with Google token -> auto provision new user
    login_res = await client.post(
        "/api/v1/auth/google",
        json={"credential": "mock_google_valid_jwt_credential"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 2. Access protected endpoint with issued JWT
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_info = me_res.json()
    assert user_info["email"] == "googleresearcher@example.com"
    assert user_info["full_name"] == "Google Researcher"
    assert user_info["role"] == "USER"
    assert user_info["tenant_id"] is not None

    # 3. Existing Google user logging in again
    second_login = await client.post(
        "/api/v1/auth/google",
        json={"credential": "mock_google_valid_jwt_credential"},
    )
    assert second_login.status_code == 200
    second_token_data = second_login.json()
    assert "access_token" in second_token_data
