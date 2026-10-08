from typing import Annotated, List

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.redis import redis_manager
from app.db.session import get_db
from app.models.user import User, UserRole
from app.security.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Dependency that extracts the JWT token, verifies not revoked, and retrieves the current user."""
    if not token:
        raise UnauthorizedException("Authentication credentials were not provided", error_code="NOT_AUTHENTICATED")

    token_data = decode_access_token(token)
    if not token_data.sub:
        raise UnauthorizedException(
            "Could not validate credentials", error_code="INVALID_TOKEN_SUB"
        )

    # Check revocation blacklist in Redis
    if token_data.jti and await redis_manager.is_token_revoked(token_data.jti):
        raise UnauthorizedException("Token has been revoked", error_code="TOKEN_REVOKED")

    stmt = select(User).where(User.id == token_data.sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User not found", error_code="USER_NOT_FOUND")
    if not user.is_active:
        raise ForbiddenException("Inactive user account", error_code="USER_INACTIVE")

    return user


def require_role(allowed_roles: List[str]):
    """Returns a dependency ensuring the current user belongs to one of allowed_roles (or is superuser)."""
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.is_superuser:
            return current_user
        if current_user.role not in allowed_roles:
            raise ForbiddenException(
                f"Operation requires one of roles: {', '.join(allowed_roles)}. Current role: {current_user.role}",
                error_code="INSUFFICIENT_PERMISSIONS",
            )
        return current_user

    return role_checker


# Standard RBAC Dependencies
async def require_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Requires active user with at least USER role."""
    return current_user


async def require_analyst(
    current_user: Annotated[User, Depends(require_role([UserRole.ANALYST.value, UserRole.ADMIN.value]))],
) -> User:
    """Requires active user with ANALYST or ADMIN role."""
    return current_user


async def require_admin(
    current_user: Annotated[User, Depends(require_role([UserRole.ADMIN.value]))],
) -> User:
    """Requires active user with ADMIN role or superuser."""
    return current_user


# Backward compatibility
async def get_current_active_superuser(
    current_user: Annotated[User, Depends(require_admin)],
) -> User:
    return current_user
