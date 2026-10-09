import time
from typing import Any, Dict, Optional

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.logging import logger

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_TOKEN_EXCHANGE_URL = "https://oauth2.googleapis.com/token"


async def verify_google_id_token(token: str) -> Dict[str, Any]:
    """Verify Google ID token / GIS credential and extract authenticated user details.
    
    Uses google-auth library first, with fallback to Google's tokeninfo endpoint.
    """
    if not token or not token.strip():
        raise UnauthorizedException("Empty Google credential provided", error_code="EMPTY_GOOGLE_TOKEN")

    cleaned_token = token.strip()
    client_id = settings.GOOGLE_CLIENT_ID.strip() if settings.GOOGLE_CLIENT_ID else None
    id_info: Optional[Dict[str, Any]] = None
    verification_error: Optional[str] = None

    # Method 1: Verify using google-auth library
    try:
        req = google_requests.Request()
        id_info = google_id_token.verify_oauth2_token(
            cleaned_token,
            req,
            audience=client_id if client_id else None,
        )
    except Exception as e:
        verification_error = str(e)
        logger.debug(f"google.oauth2 library verification failed: {e}; trying tokeninfo API")

    # Method 2: Fallback / Verification using Google's tokeninfo HTTP API
    if not id_info:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": cleaned_token})
                if resp.status_code == 200:
                    token_data = resp.json()
                    # Validate audience if client_id is configured
                    aud = token_data.get("aud")
                    if client_id and aud != client_id:
                        raise UnauthorizedException(
                            f"Google token audience mismatch (aud={aud})",
                            error_code="GOOGLE_AUDIENCE_MISMATCH",
                        )
                    # Validate expiration
                    exp = int(token_data.get("exp", 0))
                    if exp and exp < time.time():
                        raise UnauthorizedException(
                            "Google token has expired",
                            error_code="GOOGLE_TOKEN_EXPIRED",
                        )
                    id_info = token_data
                else:
                    logger.warning(
                        f"Google tokeninfo API rejected token (HTTP {resp.status_code}): {resp.text}"
                    )
        except UnauthorizedException:
            raise
        except Exception as exc:
            logger.error(f"Error contacting Google tokeninfo API: {exc}")

    if not id_info:
        raise UnauthorizedException(
            f"Could not verify Google authentication credentials: {verification_error or 'Invalid token'}",
            error_code="INVALID_GOOGLE_TOKEN",
        )

    # Validate essential claims
    email = id_info.get("email")
    if not email:
        raise UnauthorizedException(
            "Google account does not provide an email address",
            error_code="GOOGLE_EMAIL_MISSING",
        )

    email_verified = id_info.get("email_verified")
    if email_verified is not None:
        if isinstance(email_verified, str):
            email_verified = email_verified.lower() in ("true", "1")
        if not email_verified:
            raise UnauthorizedException(
                "Google account email is not verified",
                error_code="GOOGLE_EMAIL_NOT_VERIFIED",
            )

    sub = id_info.get("sub") or id_info.get("user_id")
    name = id_info.get("name") or id_info.get("given_name")
    picture = id_info.get("picture")

    return {
        "email": email.lower().strip(),
        "google_id": str(sub) if sub else None,
        "full_name": name.strip() if name else None,
        "avatar_url": picture,
        "email_verified": True,
    }


async def exchange_google_code(code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """Exchange authorization code for tokens via Google OAuth2 token endpoint."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise UnauthorizedException(
            "Google OAuth Client ID and Secret are not configured on server",
            error_code="GOOGLE_NOT_CONFIGURED",
        )

    target_redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

    payload = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": target_redirect_uri,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(GOOGLE_TOKEN_EXCHANGE_URL, data=payload)
            if resp.status_code != 200:
                logger.error(f"Failed to exchange Google authorization code: {resp.text}")
                raise UnauthorizedException(
                    "Failed to exchange Google authorization code",
                    error_code="GOOGLE_CODE_EXCHANGE_FAILED",
                )
            data = resp.json()
            id_token_str = data.get("id_token")
            if not id_token_str:
                raise UnauthorizedException(
                    "Google response missing ID token",
                    error_code="GOOGLE_ID_TOKEN_MISSING",
                )
            return await verify_google_id_token(id_token_str)
    except UnauthorizedException:
        raise
    except Exception as e:
        logger.error(f"Error during Google code exchange: {e}")
        raise UnauthorizedException(
            f"Google authorization code exchange error: {e}",
            error_code="GOOGLE_CODE_EXCHANGE_ERROR",
        )
