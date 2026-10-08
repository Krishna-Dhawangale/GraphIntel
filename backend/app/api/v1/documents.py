from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.logging import logger
from app.core.rate_limit import rate_limit
from app.db.session import AsyncSessionLocal, get_db
from app.models.audit import AuditAction
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.user import User, UserRole
from app.providers.storage.factory import get_storage_provider
from app.providers.vector_store.factory import get_vector_store
from app.schemas.chunk import DocumentChunkResponse
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusResponse,
)
from app.security.deps import get_current_user, require_user
from app.services.audit_service import log_audit_event
from app.services.ingestion_service import IngestionService
from app.workers.async_worker import background_worker

router = APIRouter()


async def _run_worker_ingestion(payload: dict) -> None:
    """Worker task callback for background ingestion."""
    doc_id = payload["document_id"]
    user_id = payload["user_id"]
    async with AsyncSessionLocal() as session:
        service = IngestionService(session)
        await service.process_document(doc_id, user_id)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60, key_prefix="doc_upload"))],
)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    sync_process: bool = Query(
        True, description="Process immediately in request for instant availability"
    ),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new document (PDF, DOCX, TXT, HTML, CSV, JSON) with validation and tenant isolation."""
    service = IngestionService(db)
    doc = await service.upload_document(
        file=file,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        title=title,
    )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    # Record audit event
    await log_audit_event(
        db=db,
        action=AuditAction.DOCUMENT_UPLOAD.value,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        resource_type="document",
        resource_id=doc.id,
        status="SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={"filename": doc.filename, "size": doc.file_size, "title": doc.title},
    )

    if sync_process:
        await service.process_document(doc.id, current_user.id)
        await db.refresh(doc)
    else:
        # Enqueue with BackgroundWorker abstraction
        await background_worker.submit_job(
            job_type="document_ingestion",
            payload={
                "document_id": doc.id,
                "user_id": current_user.id,
                "tenant_id": current_user.tenant_id,
            },
            task_func=_run_worker_ingestion,
        )

    return doc


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """List non-deleted documents scoped strictly to the authenticated user's tenant."""
    stmt = (
        select(Document)
        .where(
            Document.tenant_id == current_user.tenant_id,
            Document.is_deleted == False,
        )
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    documents = result.scalars().all()

    count_stmt = select(func.count(Document.id)).where(
        Document.tenant_id == current_user.tenant_id,
        Document.is_deleted == False,
    )
    count_res = await db.execute(count_stmt)
    total = count_res.scalar() or 0

    return DocumentListResponse(items=list(documents), total=total)


@router.get("/{id}", response_model=DocumentDetailResponse)
async def get_document(
    id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve document details by ID enforcing tenant isolation."""
    stmt = select(Document).where(Document.id == id, Document.is_deleted == False)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise NotFoundException(f"Document with ID {id} not found", error_code="DOCUMENT_NOT_FOUND")

    # Strict multi-tenant isolation check
    if doc.tenant_id != current_user.tenant_id and current_user.role != UserRole.ADMIN.value:
        raise ForbiddenException(
            "You do not have permission to access this document", error_code="ACCESS_DENIED"
        )

    chunk_count_stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == id)
    chunk_count_res = await db.execute(chunk_count_stmt)
    chunks_count = chunk_count_res.scalar() or 0

    return DocumentDetailResponse(
        id=doc.id,
        user_id=doc.user_id,
        title=doc.title,
        filename=doc.filename,
        file_size=doc.file_size,
        content_type=doc.content_type,
        storage_path=doc.storage_path,
        status=doc.status,
        error_message=doc.error_message,
        doc_metadata=doc.doc_metadata,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        chunks_count=chunks_count,
    )


@router.get("/{id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    id: str,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve document processing status with tenant isolation."""
    stmt = select(Document).where(Document.id == id, Document.is_deleted == False)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise NotFoundException(f"Document with ID {id} not found", error_code="DOCUMENT_NOT_FOUND")

    if doc.tenant_id != current_user.tenant_id and current_user.role != UserRole.ADMIN.value:
        raise ForbiddenException(
            "You do not have permission to access this document", error_code="ACCESS_DENIED"
        )

    chunk_count_stmt = select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == id)
    chunk_count_res = await db.execute(chunk_count_stmt)
    chunks_count = chunk_count_res.scalar() or 0

    return DocumentStatusResponse(
        id=doc.id,
        status=doc.status,
        error_message=doc.error_message,
        total_chunks=chunks_count,
        updated_at=doc.updated_at,
    )


@router.get("/{id}/chunks", response_model=List[DocumentChunkResponse])
async def get_document_chunks(
    id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve chunks for a given document with tenant isolation."""
    stmt = select(Document).where(Document.id == id, Document.is_deleted == False)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise NotFoundException(f"Document with ID {id} not found", error_code="DOCUMENT_NOT_FOUND")

    if doc.tenant_id != current_user.tenant_id and current_user.role != UserRole.ADMIN.value:
        raise ForbiddenException(
            "You do not have permission to access this document", error_code="ACCESS_DENIED"
        )

    chunks_stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == id)
        .order_by(DocumentChunk.chunk_index.asc())
        .offset(skip)
        .limit(limit)
    )
    chunks_res = await db.execute(chunks_stmt)
    chunks = chunks_res.scalars().all()

    return list(chunks)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    id: str,
    request: Request,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a document, pruning vector store entries and knowledge graph entries."""
    stmt = select(Document).where(Document.id == id, Document.is_deleted == False)
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise NotFoundException(f"Document with ID {id} not found", error_code="DOCUMENT_NOT_FOUND")

    # Only owner or Admin can delete
    if doc.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise ForbiddenException(
            "You do not have permission to delete this document", error_code="ACCESS_DENIED"
        )

    # 1. Delete from vector store
    vector_store = get_vector_store()
    await vector_store.delete_by_document(document_id=id, user_id=doc.user_id)

    # 2. Prune from knowledge graph store
    try:
        from app.providers.graph_store.factory import get_graph_store
        graph_store = get_graph_store()
        await graph_store.delete_document_graph_data(user_id=doc.user_id, document_id=id)
    except Exception as ge:
        logger.warning(f"Failed to prune graph data for document {id}: {ge}")

    # 3. Soft-delete in database
    doc.is_deleted = True
    doc.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    # 4. Audit Log
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await log_audit_event(
        db=db,
        action=AuditAction.DOCUMENT_DELETE.value,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        resource_type="document",
        resource_id=id,
        status="SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return None
