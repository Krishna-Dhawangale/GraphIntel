from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.audit import AuditAction, AuditLog
from app.models.user import User, UserRole
from app.schemas.user import UserResponse
from app.security.deps import require_admin
from app.services.audit_service import get_audit_logs, log_audit_event

router = APIRouter()


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    status: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata_json: dict
    created_at: str


class UpdateRoleRequest(BaseModel):
    role: str


@router.get(
    "/audit-logs",
    dependencies=[Depends(require_admin), Depends(rate_limit(max_requests=100, window_seconds=60, key_prefix="admin_audit"))],
)
async def list_audit_logs(
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve system audit logs for compliance, security analysis, and monitoring."""
    logs = await get_audit_logs(
        db=db,
        tenant_id=tenant_id,
        action=action,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "tenant_id": log.tenant_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "status": log.status,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "metadata": log.metadata_json,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get(
    "/users",
    response_model=List[UserResponse],
    dependencies=[Depends(require_admin)],
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to list all platform users."""
    stmt = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    dependencies=[Depends(require_admin)],
)
async def update_user_role(
    user_id: str,
    payload: UpdateRoleRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to update user RBAC role."""
    target_role = payload.role.upper()
    if target_role not in [r.value for r in UserRole]:
        raise NotFoundException(f"Invalid role: {target_role}", error_code="INVALID_ROLE")

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    target_user = res.scalar_one_or_none()

    if not target_user:
        raise NotFoundException(f"User with ID {user_id} not found", error_code="USER_NOT_FOUND")

    old_role = target_user.role
    target_user.role = target_role
    if target_role == UserRole.ADMIN.value:
        target_user.is_superuser = True
    await db.commit()
    await db.refresh(target_user)

    await log_audit_event(
        db=db,
        action=AuditAction.PERMISSION_CHANGE.value,
        user_id=current_admin.id,
        tenant_id=current_admin.tenant_id,
        resource_type="user",
        resource_id=target_user.id,
        status="SUCCESS",
        metadata={"old_role": old_role, "new_role": target_role},
    )

    return target_user
