import hashlib
import json
from typing import List

from fastapi import APIRouter, Depends, Request
from fastapi import Query as FastQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rate_limit import rate_limit
from app.core.redis import redis_manager
from app.db.session import get_db
from app.models.audit import AuditAction
from app.models.query import Query as QueryModel
from app.models.user import User
from app.schemas.query import QueryHistoryItem, QueryRequest, QueryResponse
from app.security.deps import get_current_user, require_user
from app.security.prompt_injection import detect_prompt_injection
from app.services.audit_service import log_audit_event
from app.services.rag_service import RAGService

router = APIRouter()


@router.post(
    "",
    response_model=QueryResponse,
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, key_prefix="query_standard"))],
)
async def execute_query(
    payload: QueryRequest,
    request: Request,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute GraphRAG query with vector search, knowledge graph traversal, hybrid fusion, or LangGraph agent."""
    # Check for adversarial prompt injection in query
    injection_check = detect_prompt_injection(payload.question)
    sanitized_question = injection_check.sanitized_text if injection_check.is_suspicious else payload.question

    # Redis cache check: query:{tenant_id}:{hash(question + filters)}
    cache_fingerprint = hashlib.sha256(
        f"{sanitized_question}_{payload.retrieval_mode}_{payload.top_k}_{payload.temporal_year}_{payload.document_ids}".encode()
    ).hexdigest()
    cache_key = f"query:{current_user.tenant_id}:{cache_fingerprint}"

    cached = await redis_manager.get_json(cache_key)
    if cached:
        return QueryResponse(**cached)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    if payload.retrieval_mode == "agentic":
        from app.agent.agent_service import AgentRAGService

        agent_svc = AgentRAGService(db)
        response = await agent_svc.execute(
            question=sanitized_question,
            user_id=current_user.id,
        )
    else:
        rag_service = RAGService(db)
        response = await rag_service.answer_query(
            question=sanitized_question,
            user_id=current_user.id,
            top_k=payload.top_k or 5,
            retrieval_mode=payload.retrieval_mode or "hybrid",
            max_graph_hops=payload.max_graph_hops or 3,
            document_ids=payload.document_ids,
            temporal_year=payload.temporal_year,
        )

    # Cache result for 5 minutes (300 seconds)
    try:
        await redis_manager.set_json(cache_key, response.model_dump(), ex=300)
    except Exception:
        pass

    # Record audit log
    await log_audit_event(
        db=db,
        action=AuditAction.QUERY.value,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        resource_type="query",
        status="SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={
            "mode": payload.retrieval_mode,
            "prompt_injection_flag": injection_check.is_suspicious,
        },
    )

    return response


@router.post(
    "/agent",
    response_model=QueryResponse,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60, key_prefix="query_agent"))],
)
async def execute_agent_query(
    payload: QueryRequest,
    request: Request,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute multi-step Agentic RAG workflow with LangGraph state graph."""
    injection_check = detect_prompt_injection(payload.question)
    sanitized_question = injection_check.sanitized_text if injection_check.is_suspicious else payload.question

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    from app.agent.agent_service import AgentRAGService

    agent_svc = AgentRAGService(db)
    response = await agent_svc.execute(
        question=sanitized_question,
        user_id=current_user.id,
    )

    await log_audit_event(
        db=db,
        action=AuditAction.QUERY.value,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        resource_type="query",
        status="SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={
            "mode": "agentic",
            "prompt_injection_flag": injection_check.is_suspicious,
        },
    )

    return response


@router.get("/history", response_model=List[QueryHistoryItem])
async def get_query_history(
    skip: int = FastQuery(0, ge=0),
    limit: int = FastQuery(20, ge=1, le=100),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve history of past RAG queries executed by the current user."""
    stmt = (
        select(QueryModel)
        .options(selectinload(QueryModel.sources))
        .where(QueryModel.user_id == current_user.id)
        .order_by(QueryModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    queries = result.scalars().all()

    items: List[QueryHistoryItem] = []
    for q in queries:
        items.append(
            QueryHistoryItem(
                id=q.id,
                question=q.question,
                answer=q.answer,
                retrieval_time_ms=q.retrieval_time_ms,
                llm_time_ms=q.llm_time_ms,
                created_at=q.created_at,
                sources_count=len(q.sources),
            )
        )

    return items
