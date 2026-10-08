from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.metrics import get_prometheus_metrics_response
from app.core.redis import redis_manager
from app.db.session import get_db
from app.providers.graph_store.factory import get_graph_store
from app.providers.storage.factory import get_storage_provider
from app.providers.vector_store.factory import get_vector_store

router = APIRouter()


@router.get("/health", summary="System Health Check")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint evaluating all core dependencies."""
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "database": "unknown",
            "storage": "unknown",
            "vector_store": "unknown",
            "graph_store": "unknown",
            "redis": "unknown",
        },
    }

    # 1. Database check
    try:
        await db.execute(text("SELECT 1"))
        health_status["services"]["database"] = "ok"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # 2. Storage check
    try:
        _ = get_storage_provider()
        health_status["services"]["storage"] = "ok"
    except Exception as e:
        health_status["services"]["storage"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # 3. Vector store check
    try:
        vs = get_vector_store()
        is_ok = await vs.health_check()
        health_status["services"]["vector_store"] = "ok" if is_ok else "unreachable"
        if not is_ok:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["vector_store"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # 4. Graph store check
    try:
        gs = get_graph_store()
        is_graph_ok = await gs.health_check()
        health_status["services"]["graph_store"] = "ok" if is_graph_ok else "unreachable"
        if not is_graph_ok:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["graph_store"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # 5. Redis check
    try:
        client = await redis_manager.get_client()
        await client.ping()
        health_status["services"]["redis"] = "ok"
    except Exception as e:
        health_status["services"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


@router.get("/health/live", summary="Kubernetes Liveness Probe")
async def liveness_probe():
    """Liveness probe: returns 200 if the web process is alive and responsive."""
    return {"status": "alive"}


@router.get("/health/ready", summary="Kubernetes Readiness Probe")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """Readiness probe: verifies critical dependencies before accepting traffic."""
    readiness = {"status": "ready", "ready": True, "details": {}}
    try:
        await db.execute(text("SELECT 1"))
        readiness["details"]["database"] = "ok"
    except Exception as e:
        readiness["details"]["database"] = f"error: {str(e)}"
        readiness["ready"] = False

    try:
        client = await redis_manager.get_client()
        await client.ping()
        readiness["details"]["redis"] = "ok"
    except Exception as e:
        readiness["details"]["redis"] = f"error: {str(e)}"
        readiness["ready"] = False

    if not readiness["ready"]:
        readiness["status"] = "not_ready"
        return Response(content=str(readiness), status_code=503, media_type="application/json")

    return readiness


@router.get("/metrics", summary="Prometheus Metrics Scrape Endpoint")
async def prometheus_metrics():
    """Prometheus exposition metrics endpoint."""
    return get_prometheus_metrics_response()
