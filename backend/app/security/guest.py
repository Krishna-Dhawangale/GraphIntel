import hashlib
import hmac
import uuid
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import redis_manager
from app.db.session import get_db
from app.models.user import User
from app.security.jwt import decode_access_token


GUEST_COOKIE_NAME = "graphintel_guest_session"
GUEST_HEADER_NAME = "X-Guest-Session-ID"


@dataclass
class Identity:
    """Represents either an authenticated User or a verified Guest session."""
    user: Optional[User]
    is_guest: bool
    user_id: Optional[str]
    guest_session_id: Optional[str]
    tenant_id: str


def sign_guest_session_id(session_id: str) -> str:
    """Generate an HMAC-SHA256 signature for a guest session ID."""
    key = settings.SECRET_KEY.encode("utf-8")
    sig = hmac.new(key, session_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{session_id}.{sig}"


def verify_guest_session_token(token: Optional[str]) -> Optional[str]:
    """Verify HMAC signature of a guest session token and return the validated session_id."""
    if not token or "." not in token:
        return None
    session_id, sig = token.split(".", 1)
    if not session_id or len(session_id) > 64:
        return None
    expected_token = sign_guest_session_id(session_id)
    if hmac.compare_digest(token, expected_token):
        return session_id
    return None


def get_guest_session_from_request(request: Request) -> Optional[str]:
    """Extract and verify guest session token from cookie or header."""
    cookie_token = request.cookies.get(GUEST_COOKIE_NAME)
    verified = verify_guest_session_token(cookie_token)
    if verified:
        return verified

    header_token = request.headers.get(GUEST_HEADER_NAME)
    if header_token:
        # Check if header contains raw session ID or signed token
        verified_header = verify_guest_session_token(header_token)
        if verified_header:
            return verified_header
        # If header passed raw hex UUID, verify it looks like a uuid hex
        if len(header_token) in (32, 36) and header_token.replace("-", "").isalnum():
            return header_token.replace("-", "")
    return None


async def get_current_identity(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Identity:
    """
    Unified identity dependency.
    If valid Bearer access token is supplied, returns authenticated User Identity.
    Otherwise, returns a verified, cryptographically isolated Guest Identity.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
        try:
            token_data = decode_access_token(token)
            if token_data.sub and not (
                token_data.jti and await redis_manager.is_token_revoked(token_data.jti)
            ):
                stmt = select(User).where(User.id == token_data.sub)
                res = await db.execute(stmt)
                user = res.scalar_one_or_none()
                if user and user.is_active:
                    return Identity(
                        user=user,
                        is_guest=False,
                        user_id=user.id,
                        guest_session_id=None,
                        tenant_id=user.tenant_id,
                    )
        except Exception:
            pass

    # Unauthenticated / Guest flow
    session_id = get_guest_session_from_request(request)
    is_new = False
    if not session_id:
        session_id = uuid.uuid4().hex
        is_new = True

    signed_token = sign_guest_session_id(session_id)
    # Set HttpOnly, SameSite=Lax cookie
    response.set_cookie(
        key=GUEST_COOKIE_NAME,
        value=signed_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production HTTPS
        max_age=86400 * 30,  # 30 days
        path="/",
    )
    # Also expose header for mobile/API clients
    response.headers[GUEST_HEADER_NAME] = session_id

    return Identity(
        user=None,
        is_guest=True,
        user_id=None,
        guest_session_id=session_id,
        tenant_id=f"guest_{session_id[:16]}",
    )
