import secrets
import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, UnauthorizedException
from app.core.rate_limit import rate_limit
from app.core.redis import redis_manager
from app.db.session import get_db
from app.models.audit import AuditAction
from app.models.user import User, UserRole
from app.schemas.auth import (
    GoogleConfigResponse,
    GoogleLoginRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
)
from app.schemas.user import UserResponse
from app.security.deps import get_current_user
from app.security.google_auth import exchange_google_code, verify_google_id_token
from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.security.password import get_password_hash, verify_password
from app.services.audit_service import log_audit_event

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60, key_prefix="auth_register"))],
)
async def register_user(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account with default or specified role and isolated tenant."""
    # Check if email is already taken
    stmt = select(User).where(User.email == payload.email.lower().strip())
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise BadRequestException(
            "An account with this email already exists", error_code="EMAIL_EXISTS"
        )

    # Validate role or default to USER
    role_val = payload.role.upper() if payload.role else UserRole.USER.value
    if role_val not in [r.value for r in UserRole]:
        role_val = UserRole.USER.value

    # Assign unique tenant_id for multi-tenant isolation
    tenant_id = str(uuid.uuid4())

    user = User(
        email=payload.email.lower().strip(),
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=role_val,
        tenant_id=tenant_id,
        is_superuser=(role_val == UserRole.ADMIN.value),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await log_audit_event(
        db=db,
        action=AuditAction.REGISTER.value,
        user_id=user.id,
        tenant_id=user.tenant_id,
        resource_type="user",
        resource_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={"email": user.email, "role": user.role},
    )

    return user


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60, key_prefix="auth_login"))],
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """OAuth2 form login endpoint issuing access and refresh tokens."""
    email = form_data.username.lower().strip()
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    if not user or not verify_password(form_data.password, user.hashed_password):
        await log_audit_event(
            db=db,
            action=AuditAction.LOGIN.value,
            status="FAILURE",
            ip_address=client_ip,
            user_agent=user_agent,
            metadata={"email": email, "reason": "invalid_credentials"},
        )
        raise UnauthorizedException("Incorrect email or password", error_code="INVALID_CREDENTIALS")

    if not user.is_active:
        raise UnauthorizedException("User account is inactive", error_code="INACTIVE_USER")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        tenant_id=user.tenant_id,
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(subject=user.id, tenant_id=user.tenant_id)

    await log_audit_event(
        db=db,
        action=AuditAction.LOGIN.value,
        user_id=user.id,
        tenant_id=user.tenant_id,
        status="SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login/json",
    response_model=Token,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60, key_prefix="auth_login_json"))],
)
async def login_json(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """JSON body login endpoint for modern SPAs."""
    email = payload.email.lower().strip()
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    if not user or not verify_password(payload.password, user.hashed_password):
        await log_audit_event(
            db=db,
            action=AuditAction.LOGIN.value,
            status="FAILURE",
            ip_address=client_ip,
            user_agent=user_agent,
            metadata={"email": email, "reason": "invalid_credentials"},
        )
        raise UnauthorizedException("Incorrect email or password", error_code="INVALID_CREDENTIALS")

    if not user.is_active:
        raise UnauthorizedException("User account is inactive", error_code="INACTIVE_USER")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        tenant_id=user.tenant_id,
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(subject=user.id, tenant_id=user.tenant_id)

    await log_audit_event(
        db=db,
        action=AuditAction.LOGIN.value,
        user_id=user.id,
        tenant_id=user.tenant_id,
        status="SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/google/config", response_model=GoogleConfigResponse)
async def get_google_auth_config():
    """Retrieve Google OAuth client ID and availability for frontend GIS integration."""
    return GoogleConfigResponse(
        client_id=settings.GOOGLE_CLIENT_ID or "",
        enabled=bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_ID.strip()),
    )


@router.post(
    "/google",
    response_model=Token,
    dependencies=[Depends(rate_limit(max_requests=15, window_seconds=60, key_prefix="auth_google"))],
)
async def login_google(
    payload: GoogleLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with Google account via ID token / credential or authorization code.

    Validates Google identity, auto-provisions a tenant-isolated user if new, and
    issues standard GraphIntel JWT access and refresh tokens.
    """
    token_str = payload.credential or payload.id_token
    google_user_info = None

    if token_str:
        google_user_info = await verify_google_id_token(token_str)
    elif payload.code:
        google_user_info = await exchange_google_code(payload.code)
    else:
        raise BadRequestException(
            "Missing Google credential, id_token, or authorization code",
            error_code="MISSING_GOOGLE_CREDENTIAL",
        )

    email = google_user_info["email"]
    full_name = google_user_info.get("full_name")
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    # Check if user already exists
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if user:
        if not user.is_active:
            await log_audit_event(
                db=db,
                action=AuditAction.LOGIN.value,
                user_id=user.id,
                tenant_id=user.tenant_id,
                status="FAILURE",
                ip_address=client_ip,
                user_agent=user_agent,
                metadata={"email": email, "auth_provider": "google", "reason": "inactive_account"},
            )
            raise UnauthorizedException("User account is inactive", error_code="INACTIVE_USER")

        # Update full_name if user previously had none
        if not user.full_name and full_name:
            user.full_name = full_name
            await db.commit()
            await db.refresh(user)
    else:
        # Auto-provision new user with isolated tenant
        tenant_id = str(uuid.uuid4())
        random_pwd_token = secrets.token_urlsafe(32)
        user = User(
            email=email,
            hashed_password=get_password_hash(f"oauth2_google_{random_pwd_token}"),
            full_name=full_name,
            role=UserRole.USER.value,
            tenant_id=tenant_id,
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        await log_audit_event(
            db=db,
            action=AuditAction.REGISTER.value,
            user_id=user.id,
            tenant_id=user.tenant_id,
            resource_type="user",
            resource_id=user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            metadata={"email": user.email, "role": user.role, "auth_provider": "google"},
        )

    # Issue GraphIntel JWT access and refresh tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        tenant_id=user.tenant_id,
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(subject=user.id, tenant_id=user.tenant_id)

    await log_audit_event(
        db=db,
        action=AuditAction.LOGIN.value,
        user_id=user.id,
        tenant_id=user.tenant_id,
        status="SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={"email": user.email, "auth_provider": "google"},
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=Token,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60, key_prefix="auth_refresh"))],
)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate refresh token and issue a fresh access and rotated refresh token."""
    token_data = decode_refresh_token(payload.refresh_token)

    if token_data.jti and await redis_manager.is_token_revoked(token_data.jti):
        raise UnauthorizedException("Refresh token has been revoked", error_code="TOKEN_REVOKED")

    stmt = select(User).where(User.id == token_data.sub)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedException("User not found or inactive", error_code="USER_INACTIVE")

    # Invalidate old refresh token (refresh token rotation)
    if token_data.jti:
        await redis_manager.revoke_token(token_data.jti, expire_seconds=86400 * 7)

    # Issue new pair
    new_access = create_access_token(subject=user.id, role=user.role, tenant_id=user.tenant_id)
    new_refresh = create_refresh_token(subject=user.id, tenant_id=user.tenant_id)

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    payload: LogoutRequest = None,
    authorization: Annotated[str, Header()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke active JWT access token and optional refresh token."""
    # Revoke access token
    if authorization and authorization.startswith("Bearer "):
        token_str = authorization.replace("Bearer ", "").strip()
        try:
            token_payload = decode_access_token(token_str)
            if token_payload.jti:
                await redis_manager.revoke_token(token_payload.jti, expire_seconds=86400)
        except Exception:
            pass

    # Revoke refresh token if provided
    if payload and payload.refresh_token:
        try:
            rt_payload = decode_refresh_token(payload.refresh_token)
            if rt_payload.jti:
                await redis_manager.revoke_token(rt_payload.jti, expire_seconds=86400 * 7)
        except Exception:
            pass

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await log_audit_event(
        db=db,
        action=AuditAction.LOGOUT.value,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        status="SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return {"message": "Successfully logged out. Tokens have been revoked."}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Retrieve currently authenticated user profile including RBAC role and tenant ID."""
    return current_user
