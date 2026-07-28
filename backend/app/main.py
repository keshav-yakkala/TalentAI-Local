"""
TalentAI — FastAPI Application Entry Point

Architecture:
  React Frontend → FastAPI → Services → LangGraph → LLM/RAG → PostgreSQL/pgvector

Security:
  - JWT auth on all non-public routes
  - organization_id resolved from DB, never from JWT claims
  - Cross-tenant isolation enforced at query level, not prompt level
  - No stack traces exposed in error responses
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CrossTenantAccessError,
    LLMOutputValidationError,
    LLMProviderError,
    ResumeParsingError,
    TalentAIBaseError,
    UnsupportedFileError,
    WorkflowError,
)
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    setup_logging()
    logger.info("TalentAI backend starting", version=settings.APP_VERSION, env=settings.ENVIRONMENT)

    # Auto-create tables (idempotent — safe to run on every start)
    try:
        import app.models  # noqa: F401 — ensures all models are registered
        from app.db.session import engine
        from app.db.base import Base
        from sqlalchemy import text

        async with engine.begin() as conn:
            # Enable pgvector extension if postgresql
            if "postgresql" in str(engine.url):
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                except Exception as e:
                    logger.warning("Could not enable pgvector extension", error=str(e))
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready")
    except Exception as exc:
        logger.warning("DB init skipped (no connection?)", error=str(exc))

    yield

    logger.info("TalentAI backend shutting down")


app = FastAPI(
    title="TalentAI API",
    description="""
    ## TalentAI — Agentic AI Recruitment Intelligence Platform

    Production-grade API for AI-assisted recruitment including:
    - Resume ingestion and intelligent parsing
    - JD analysis and requirement extraction
    - Evidence-based candidate screening
    - Adaptive AI interviews with Whisper voice support
    - Explainable scoring and recruiter tools

    **Security**: All endpoints require Bearer JWT authentication.
    Organization data is strictly isolated — cross-tenant access is blocked at the database level.
    """,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception Handlers ────────────────────────────────────────────────────────


@app.exception_handler(CrossTenantAccessError)
async def cross_tenant_handler(request: Request, exc: CrossTenantAccessError) -> JSONResponse:
    """Log critical security violation but return generic 403."""
    logger.critical(
        "CROSS_TENANT_ACCESS_ATTEMPT",
        path=str(request.url),
        message=exc.message,
    )
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"success": False, "error": "Access denied"},
    )


@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"success": False, "error": exc.message},
    )


@app.exception_handler(AuthorizationError)
async def authz_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"success": False, "error": exc.message},
    )


@app.exception_handler(UnsupportedFileError)
async def unsupported_file_handler(request: Request, exc: UnsupportedFileError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        content={"success": False, "error": exc.message},
    )


@app.exception_handler(ResumeParsingError)
async def resume_parsing_handler(request: Request, exc: ResumeParsingError) -> JSONResponse:
    logger.warning("Resume parsing failed", details=exc.details)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "error": exc.message},
    )


@app.exception_handler(LLMProviderError)
async def llm_error_handler(request: Request, exc: LLMProviderError) -> JSONResponse:
    logger.error("LLM provider error", message=exc.message)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"success": False, "error": "AI service temporarily unavailable. Please try again."},
    )


@app.exception_handler(LLMOutputValidationError)
async def llm_output_error_handler(request: Request, exc: LLMOutputValidationError) -> JSONResponse:
    logger.warning("LLM output validation failed", message=exc.message)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"success": False, "error": "AI output validation failed. Routed for human review."},
    )


@app.exception_handler(WorkflowError)
async def workflow_error_handler(request: Request, exc: WorkflowError) -> JSONResponse:
    logger.error("Workflow error", message=exc.message, details=exc.details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": "Workflow processing error. Please retry or contact support."},
    )


@app.exception_handler(TalentAIBaseError)
async def base_error_handler(request: Request, exc: TalentAIBaseError) -> JSONResponse:
    logger.error("Unhandled domain error", error=type(exc).__name__, message=exc.message)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": "An internal error occurred"},
    )


# ── Routes ────────────────────────────────────────────────────────────────────

from app.api.routes import auth, jobs, resumes, applications, interviews, analytics  # noqa: E402

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(jobs.router, prefix=settings.API_V1_PREFIX)
app.include_router(resumes.router, prefix=settings.API_V1_PREFIX)
app.include_router(applications.router, prefix=settings.API_V1_PREFIX)
app.include_router(interviews.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)


# ── Health Check ──────────────────────────────────────────────────────────────


@app.get("/health", tags=["Health"], summary="Health check endpoint")
async def health_check() -> dict:
    """
    Returns basic health status.
    Used by Docker health checks and load balancers.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"message": f"TalentAI API v{settings.APP_VERSION} — see /api/docs"}
