import functools
from typing import Callable, Optional

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging import request_id_ctx
from app.core.redis import redis_manager


class RateLimitExceededException(HTTPException):
    def __init__(self, retry_after: int = 60, message: str = None):
        detail = {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": message or f"Rate limit exceeded. Try again in {retry_after} seconds.",
            "retry_after": retry_after,
            "request_id": request_id_ctx.get(),
        }
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit(max_requests: int = 60, window_seconds: int = 60, key_prefix: str = "general"):
    """
    FastAPI dependency / decorator to enforce rate limits per IP or authenticated user/tenant.
    """
    async def dependency(request: Request):
        if not settings.RATE_LIMIT_ENABLED:
            return

        # Determine identifier: user ID from auth header if present, or client IP
        auth_header = request.headers.get("Authorization", "")
        client_ip = request.client.host if request.client else "unknown_ip"
        
        # Identifier can be IP or token hash
        if auth_header.startswith("Bearer "):
            identifier = f"user_{auth_header[-16:]}"
        else:
            identifier = f"ip_{client_ip}"

        limit_key = f"{key_prefix}:{identifier}"
        allowed, remaining, retry_after = await redis_manager.check_rate_limit(
            key=limit_key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        if not allowed:
            raise RateLimitExceededException(
                retry_after=retry_after or window_seconds,
                message=f"Rate limit of {max_requests} requests per {window_seconds}s exceeded. Try again in {retry_after or window_seconds} seconds.",
            )

    return dependency
