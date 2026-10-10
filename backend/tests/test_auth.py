import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.v1 import auth
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.security.password import verify_password


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
async def test_forgot_and_reset_password_flow(client, db_session, test_user: User, monkeypatch):
    sent_emails = []

    def fake_send_email(email: str, token: str, full_name: str | None) -> bool:
        sent_emails.append((email, token, full_name))
        return True

    monkeypatch.setattr(auth, "send_password_reset_email", fake_send_email)

    forgot_response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user.email},
    )
    assert forgot_response.status_code == 200
    assert len(sent_emails) == 1
    assert sent_emails[0][0] == test_user.email

    reset_token = (
        await db_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == test_user.id)
        )
    ).scalar_one()
    assert reset_token.token_hash == hashlib.sha256(sent_emails[0][1].encode()).hexdigest()
    assert reset_token.token_hash != sent_emails[0][1]

    new_password = "NewSecurePassword2026!"
    reset_response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": sent_emails[0][1], "new_password": new_password},
    )
    assert reset_response.status_code == 200
    await db_session.refresh(test_user)
    assert verify_password(new_password, test_user.hashed_password)

    reused_response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": sent_emails[0][1], "new_password": "AnotherSecurePassword2026!"},
    )
    assert reused_response.status_code == 400


@pytest.mark.asyncio
async def test_forgot_password_does_not_reveal_unknown_email(client: AsyncClient, monkeypatch):
    sent_emails = []
    monkeypatch.setattr(
        auth,
        "send_password_reset_email",
        lambda *args: sent_emails.append(args) or True,
    )

    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "unknown@graphintel.ai"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "If an account with that email exists, a password reset link has been sent."
    )
    assert sent_emails == []


@pytest.mark.asyncio
async def test_failed_reset_email_invalidates_token(client, db_session, test_user: User, monkeypatch):
    monkeypatch.setattr(auth, "send_password_reset_email", lambda *args: False)

    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user.email},
    )
    reset_token = (
        await db_session.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == test_user.id)
        )
    ).scalar_one()

    assert response.status_code == 200
    assert reset_token.is_used


@pytest.mark.asyncio
async def test_expired_password_reset_token_is_rejected(
    client: AsyncClient, db_session, test_user: User
):
    raw_token = "expired-reset-token"
    db_session.add(
        PasswordResetToken(
            user_id=test_user.id,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "NewSecurePassword2026!"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_RESET_TOKEN"
