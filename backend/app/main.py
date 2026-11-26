"""FastAPI Application Entrypoint for the Financial Markets Intelligence Platform (FMIP)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import (
    assistant,
    auth,
    competitors,
    intelligence_memory,
    macro,
    markets,
    opportunities,
    overview,
    regulatory,
    reports,
    webhooks,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.core.rate_limit import rate_limiter
from app.db.session import get_engine, get_session_factory, init_database_schema
from app.services.seed_service import bootstrap_platform_data

logger = get_logger("fmip.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database schema and bootstrap verified baseline data on application startup."""
    init_database_schema()
    session_factory = get_session_factory()
    with session_factory() as db:
        bootstrap_platform_data(db, run_live_network_fetch=False)
    logger.info("FMIP Backend initialized and ready.")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description=(
        "Institutional AI-Powered Financial Markets Intelligence Platform "
        "with Verified Source-of-Truth Governance & Historical Research Memory."
    ),
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Enforce API rate limiting across all incoming HTTP requests."""
    client_ip = request.client.host if request.client else "local"
    allowed, remaining = rate_limiter.check_rate_limit(
        key=f"ip:{client_ip}",
        limit=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    )
    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "API rate limit exceeded. Please retry after 60 seconds."},
        )
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response


# Register all 11 v1 Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(overview.router, prefix=settings.API_V1_STR)
app.include_router(markets.router, prefix=settings.API_V1_STR)
app.include_router(macro.router, prefix=settings.API_V1_STR)
app.include_router(opportunities.router, prefix=settings.API_V1_STR)
app.include_router(competitors.router, prefix=settings.API_V1_STR)
app.include_router(regulatory.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(assistant.router, prefix=settings.API_V1_STR)
app.include_router(webhooks.router, prefix=settings.API_V1_STR)
app.include_router(intelligence_memory.router, prefix=settings.API_V1_STR)



@app.get("/health", tags=["System Health"])
def health_check() -> Dict[str, Any]:
    """System health, database dialect, and provider status check."""
    engine = get_engine()
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "database_dialect": engine.dialect.name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
