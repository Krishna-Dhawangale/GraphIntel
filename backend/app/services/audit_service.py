import logging
from typing import Any, Dict, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditAction, AuditLog

logger = logging.getLogger(__name__)

# Sanitization set for sensitive keys
SENSITIVE_KEYS = {"password", "token", "secret", "access_token", "refresh_token", "api_key", "authorization"}


def sanitize_metadata(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not data:
        return {}
    sanitized = {}
    for k, v in data.items():
        if any(s in k.lower() for s in SENSITIVE_KEYS):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_metadata(v)
        else:
            sanitized[k] = v
    return sanitized


async def log_audit_event(
    db: AsyncSession,
    action: str,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    status: str = "SUCCESS",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Persists an audit event to the database with credentials and secrets automatically sanitized.
    """
    try:
        clean_meta = sanitize_metadata(metadata)
        audit_entry = AuditLog(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=clean_meta,
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)
        return audit_entry
    except Exception as e:
        logger.error(f"Failed to record audit log for action '{action}': {e}")
        # Audit logging failure should not break the business transaction
        await db.rollback()
        return None


async def get_audit_logs(
    db: AsyncSession,
    tenant_id: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    stmt = select(AuditLog)
    if tenant_id:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    stmt = stmt.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()
