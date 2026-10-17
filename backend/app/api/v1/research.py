from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, UnauthorizedException
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.research_history import (
    MigrateGuestHistoryRequest,
    MigrateGuestHistoryResponse,
    ResearchHistoryDetail,
    ResearchHistoryListResponse,
)
from app.security.deps import require_user
from app.security.guest import Identity, get_current_identity, get_guest_session_from_request
from app.services.research_history_service import ResearchHistoryService

router = APIRouter()


@router.get(
    "/history",
    response_model=ResearchHistoryListResponse,
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, key_prefix="res_hist_list"))],
)
async def list_research_history(
    q: Optional[str] = Query(None, description="Search term in question or answer"),
    retrieval_mode: Optional[str] = Query(None, description="Filter by retrieval mode"),
    start_date: Optional[datetime] = Query(None, description="Filter from start date"),
    end_date: Optional[datetime] = Query(None, description="Filter to end date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve isolated research history for current user or guest session."""
    service = ResearchHistoryService(db)
    items, total = await service.list_history(
        user_id=identity.user_id,
        guest_session_id=identity.guest_session_id,
        q=q,
        retrieval_mode=retrieval_mode,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return ResearchHistoryListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/history/{history_id}",
    response_model=ResearchHistoryDetail,
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, key_prefix="res_hist_detail"))],
)
async def get_research_history_item(
    history_id: str,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve complete detail of a past research query enforcing ownership."""
    service = ResearchHistoryService(db)
    detail = await service.get_history_detail(
        history_id=history_id,
        user_id=identity.user_id,
        guest_session_id=identity.guest_session_id,
    )
    if not detail:
        raise NotFoundException(f"Research history record '{history_id}' not found.")
    return detail


@router.delete(
    "/history/{history_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60, key_prefix="res_hist_del"))],
)
async def delete_research_history_item(
    history_id: str,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single research history item if owned by caller."""
    service = ResearchHistoryService(db)
    deleted = await service.delete_history_item(
        history_id=history_id,
        user_id=identity.user_id,
        guest_session_id=identity.guest_session_id,
    )
    if not deleted:
        raise NotFoundException(f"Research history record '{history_id}' not found.")
    return {"message": "History entry deleted successfully.", "id": history_id}


@router.delete(
    "/history",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60, key_prefix="res_hist_clear"))],
)
async def clear_research_history(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Clear all research history belonging to current user or guest session."""
    service = ResearchHistoryService(db)
    cleared_count = await service.clear_history(
        user_id=identity.user_id,
        guest_session_id=identity.guest_session_id,
    )
    return {
        "message": f"Successfully cleared {cleared_count} history records.",
        "cleared_count": cleared_count,
    }


@router.post(
    "/history/migrate",
    response_model=MigrateGuestHistoryResponse,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60, key_prefix="res_hist_migrate"))],
)
async def migrate_guest_history_to_account(
    request: Request,
    payload: MigrateGuestHistoryRequest,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    """
    Migrate guest research history to authenticated account after login/registration.
    Requires an authenticated user session.
    """
    if identity.is_guest or not identity.user_id:
        raise UnauthorizedException("Must be signed in to migrate guest history.", error_code="AUTHENTICATION_REQUIRED")

    # Determine guest session ID from request body, cookie, or header
    guest_session_id = payload.guest_session_id or get_guest_session_from_request(request)
    if not guest_session_id:
        return MigrateGuestHistoryResponse(
            migrated_count=0,
            message="No verified guest session found to migrate.",
        )

    service = ResearchHistoryService(db)
    migrated_count = await service.migrate_guest_history(
        guest_session_id=guest_session_id,
        target_user_id=identity.user_id,
    )
    return MigrateGuestHistoryResponse(
        migrated_count=migrated_count,
        message=f"Successfully migrated {migrated_count} research records to account.",
    )
