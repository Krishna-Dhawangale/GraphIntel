import asyncio
import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, UnauthorizedException
from app.core.rate_limit import rate_limit
from app.core.redis import redis_manager
from app.db.session import get_db
from app.models.audit import AuditAction
from app.models.password_reset import PasswordResetToken
from app.models.user import User, UserRole
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    Token,
)
from app.schemas.user import UserResponse
from app.security.deps import get_current_user
from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.security.password import get_password_hash, verify_password
from app.services.audit_service import log_audit_event
from app.services.email_service import send_password_reset_email

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


# ---------------------------------------------------------------------------
# Password Reset Flow
# ---------------------------------------------------------------------------

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=300, key_prefix="forgot_pwd"))],
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset link.

    Always returns the same success message regardless of whether the email
    exists, to prevent user enumeration attacks.
    """
    # Locate user — silently ignore if not found (anti-enumeration)
    stmt = select(User).where(User.email == payload.email.lower().strip())
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if user and user.is_active:
        # Invalidate any previous unused tokens for this user
        await db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_used == False,  # noqa: E712
            )
            .values(is_used=True)
        )

        # Create a new reset token
        raw_token = secrets.token_urlsafe(64)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        )
        db.add(reset_token)
        await db.commit()
        await db.refresh(reset_token)

        # Send email in a thread so it doesn't block the event loop
        email_sent = await asyncio.to_thread(
            send_password_reset_email,
            user.email,
            raw_token,
            user.full_name,
        )
        if not email_sent:
            reset_token.is_used = True
            await db.commit()

        client_ip = request.client.host if request.client else None
        await log_audit_event(
            db=db,
            action="PASSWORD_RESET_REQUEST",
            user_id=user.id,
            tenant_id=user.tenant_id,
            ip_address=client_ip,
            metadata={"email": user.email},
        )

    # Always return the same response (anti-enumeration)
    return MessageResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=300, key_prefix="reset_pwd"))],
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Consume a valid reset token and update the user's password.
    Tokens are single-use and expire after 30 minutes.
    """
    # Look up the token (joined with user)
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    res = await db.execute(stmt)
    reset_token = res.scalar_one_or_none()

    if not reset_token or not reset_token.is_valid:
        raise BadRequestException(
            "This password reset link is invalid or has expired. Please request a new one.",
            error_code="INVALID_RESET_TOKEN",
        )

    user = reset_token.user
    if not user or not user.is_active:
        raise BadRequestException(
            "Account not found or inactive.",
            error_code="USER_INACTIVE",
        )

    # Update password and mark token as used
    user.hashed_password = get_password_hash(payload.new_password)
    reset_token.is_used = True
    await db.commit()

    client_ip = request.client.host if request.client else None
    await log_audit_event(
        db=db,
        action="PASSWORD_RESET_SUCCESS",
        user_id=user.id,
        tenant_id=user.tenant_id,
        ip_address=client_ip,
        metadata={"email": user.email},
    )

    return MessageResponse(message="Your password has been updated successfully. You can now log in.")
