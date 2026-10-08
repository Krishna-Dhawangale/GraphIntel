import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.schemas.auth import TokenPayload


def create_access_token(
    subject: str,
    role: str = "USER",
    tenant_id: str = "",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token for the given subject (user ID)."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    jti = str(uuid.uuid4())
    to_encode: Dict[str, Any] = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "role": role,
        "tenant_id": str(tenant_id),
        "type": "access",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str,
    tenant_id: str = "",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT refresh token with longer validity."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    jti = str(uuid.uuid4())
    to_encode: Dict[str, Any] = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "tenant_id": str(tenant_id),
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.type and token_data.type != "access":
            raise UnauthorizedException("Invalid token type for access", error_code="INVALID_TOKEN_TYPE")
        return token_data
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired", error_code="TOKEN_EXPIRED")
    except (jwt.PyJWTError, Exception):
        raise UnauthorizedException("Could not validate credentials", error_code="INVALID_TOKEN")


def decode_refresh_token(token: str) -> TokenPayload:
    """Decode and validate a JWT refresh token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.type != "refresh":
            raise UnauthorizedException("Invalid token type for refresh", error_code="INVALID_TOKEN_TYPE")
        return token_data
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Refresh token has expired", error_code="REFRESH_TOKEN_EXPIRED")
    except (jwt.PyJWTError, Exception):
        raise UnauthorizedException("Could not validate refresh token", error_code="INVALID_REFRESH_TOKEN")
