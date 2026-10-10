import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.exceptions import GraphIntelException
from app.core.logging import logger, request_id_ctx
from app.core.rate_limit import RateLimitExceededException
from app.core.redis import redis_manager
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.base import init_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables are created if running standalone
    try:
        await init_models()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error during startup table initialization: {e}")
    
    # Initialize redis connection
    await redis_manager.get_client()

    yield
    # Shutdown logic
    await redis_manager.close()
    logger.info("Application shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Enterprise Market Intelligence GraphRAG Platform (Production Backend)",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Trusted Host Middleware
if settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
    class ExemptHealthTrustedHostMiddleware:
        """Allow internal container health check probes (Render/K8s) even when host validation is enforced."""
        def __init__(self, app, allowed_hosts: list[str]):
            self.app = app
            self.inner = TrustedHostMiddleware(app, allowed_hosts=allowed_hosts)

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                path = scope.get("path", "")
                if path.startswith("/api/v1/health") or path in ("/", "/health"):
                    return await self.app(scope, receive, send)
            return await self.inner(scope, receive, send)

    effective_allowed_hosts = list(settings.ALLOWED_HOSTS)
    for host in ["localhost", "127.0.0.1", "*.onrender.com"]:
        if host not in effective_allowed_hosts:
            effective_allowed_hosts.append(host)

    app.add_middleware(ExemptHealthTrustedHostMiddleware, allowed_hosts=effective_allowed_hosts)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID, Timing, and Request Size Middleware
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    # Request body size limit check
    content_length = request.headers.get("content-length")
    max_bytes = settings.MAX_REQUEST_BODY_SIZE_MB * 1024 * 1024
    if content_length and int(content_length) > max_bytes:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "error": {
                    "code": "REQUEST_TOO_LARGE",
                    "message": f"Request size exceeds limit of {settings.MAX_REQUEST_BODY_SIZE_MB}MB",
                }
            },
        )

    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_ctx.set(req_id)
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        try:
            from app.core.metrics import record_request_metrics
            record_request_metrics(request.method, request.url.path, response.status_code, process_time)
        except Exception:
            pass
        return response
    finally:
        request_id_ctx.reset(token)


# Exception Handlers
@app.exception_handler(RateLimitExceededException)
async def rate_limit_handler(request: Request, exc: RateLimitExceededException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"error": exc.detail},
    )


@app.exception_handler(GraphIntelException)
async def graphintel_exception_handler(request: Request, exc: GraphIntelException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "extra": exc.extra,
                "request_id": request_id_ctx.get(),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": exc.errors(),
                "request_id": request_id_ctx.get(),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error: {exc}")
    # Never expose internal traceback, DB queries, or credentials to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal error occurred. Please try again later.",
                "request_id": request_id_ctx.get(),
            }
        },
    )


# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": f"{settings.API_V1_PREFIX}/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
