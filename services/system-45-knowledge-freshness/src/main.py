"""FastAPI application entry point for System 45 - Knowledge Freshness Service.

Initialises database pool, Qdrant client, Redis, APScheduler, and
registers all API routers including /health and /metrics.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
import structlog
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

from src.config import settings
from src.models import HealthResponse
from src.routers import feeds, reports, updates
from src.services.freshness import FreshnessService
from src.services.scheduler import FreshnessScheduler

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
REGISTRY = CollectorRegistry()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
    registry=REGISTRY,
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    registry=REGISTRY,
)
SCAN_COUNT = Counter(
    "feed_scans_total",
    "Total feed scan cycles executed",
    registry=REGISTRY,
)
UPDATES_STORED = Counter(
    "updates_stored_total",
    "Total knowledge updates stored in Qdrant",
    registry=REGISTRY,
)

# ---------------------------------------------------------------------------
# Application startup time tracking
# ---------------------------------------------------------------------------
_start_time: float = 0.0


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan managing connections and the scheduler."""
    global _start_time
    _start_time = time.monotonic()

    logger.info(
        "service_starting",
        service=settings.SERVICE_NAME,
        port=settings.SERVICE_PORT,
    )

    # --- Shared HTTP client ------------------------------------------------
    http_client = httpx.AsyncClient(timeout=60.0)
    app.state.http_client = http_client

    # --- Database pool (asyncpg) -------------------------------------------
    db_pool = None
    try:
        import asyncpg

        dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        db_pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
        # Ensure the deprecation_warnings table exists
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS deprecation_warnings (
                    id SERIAL PRIMARY KEY,
                    package TEXT NOT NULL,
                    old_version TEXT NOT NULL DEFAULT '',
                    new_version TEXT NOT NULL DEFAULT '',
                    deprecation_type TEXT NOT NULL DEFAULT 'api_change',
                    migration_guide TEXT NOT NULL DEFAULT '',
                    severity TEXT NOT NULL DEFAULT 'medium',
                    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (package, new_version)
                )
                """
            )
        logger.info("database_pool_created")
    except Exception as exc:
        logger.warning("database_pool_unavailable", error=str(exc))
    app.state.db_pool = db_pool

    # --- Qdrant client -----------------------------------------------------
    qdrant_client = None
    try:
        from qdrant_client import AsyncQdrantClient

        qdrant_url = settings.QDRANT_URL
        qdrant_client = AsyncQdrantClient(url=qdrant_url)
        logger.info("qdrant_client_created", url=qdrant_url)
    except Exception as exc:
        logger.warning("qdrant_client_unavailable", error=str(exc))
    app.state.qdrant_client = qdrant_client

    # --- Redis client ------------------------------------------------------
    redis_client = None
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        await redis_client.ping()
        logger.info("redis_client_created")
    except Exception as exc:
        logger.warning("redis_client_unavailable", error=str(exc))
    app.state.redis_client = redis_client

    # --- Freshness service -------------------------------------------------
    freshness_service = FreshnessService(
        qdrant_client=qdrant_client,
        http_client=http_client,
        db_pool=db_pool,
        redis_client=redis_client,
    )
    app.state.freshness_service = freshness_service

    # --- Scheduler ---------------------------------------------------------
    scheduler = FreshnessScheduler()
    scheduler.configure(freshness_service)
    scheduler.start()
    app.state.scheduler = scheduler

    logger.info("service_started", service=settings.SERVICE_NAME)

    yield

    # --- Shutdown ----------------------------------------------------------
    logger.info("service_shutting_down")
    scheduler.stop()

    if redis_client is not None:
        await redis_client.aclose()
    if db_pool is not None:
        await db_pool.close()
    if qdrant_client is not None:
        await qdrant_client.close()
    await http_client.aclose()

    logger.info("service_stopped")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="System 45 - Knowledge Freshness Service",
    description=(
        "Monitors software ecosystem feeds for breaking changes, deprecations, "
        "security advisories, and best practices. Scores relevance via AI and "
        "stores high-value updates in Qdrant for retrieval-augmented generation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware — request metrics
# ---------------------------------------------------------------------------


@app.middleware("http")
async def metrics_middleware(request: Request, call_next: object) -> Response:
    """Record Prometheus metrics for every HTTP request."""
    start = time.monotonic()
    response: Response = await call_next(request)  # type: ignore[arg-type]
    duration = time.monotonic() - start

    path = request.url.path
    REQUEST_COUNT.labels(
        method=request.method,
        path=path,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, path=path).observe(duration)

    return response


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check(request: Request) -> HealthResponse:
    """Health check endpoint for container orchestration."""
    checks: dict[str, str] = {}

    # Database
    db_pool = getattr(request.app.state, "db_pool", None)
    if db_pool is not None:
        try:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            checks["database"] = "healthy"
        except Exception:
            checks["database"] = "unhealthy"
    else:
        checks["database"] = "not_configured"

    # Redis
    redis_client = getattr(request.app.state, "redis_client", None)
    if redis_client is not None:
        try:
            await redis_client.ping()
            checks["redis"] = "healthy"
        except Exception:
            checks["redis"] = "unhealthy"
    else:
        checks["redis"] = "not_configured"

    # Qdrant
    qdrant_client = getattr(request.app.state, "qdrant_client", None)
    if qdrant_client is not None:
        try:
            await qdrant_client.get_collections()
            checks["qdrant"] = "healthy"
        except Exception:
            checks["qdrant"] = "unhealthy"
    else:
        checks["qdrant"] = "not_configured"

    # Scheduler
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is not None:
        jobs = scheduler.get_jobs()
        checks["scheduler"] = f"running ({len(jobs)} jobs)"
    else:
        checks["scheduler"] = "not_started"

    uptime = time.monotonic() - _start_time if _start_time > 0 else 0.0

    overall = "healthy" if "unhealthy" not in checks.values() else "degraded"

    return HealthResponse(
        status=overall,
        service=settings.SERVICE_NAME,
        version="1.0.0",
        uptime_seconds=round(uptime, 2),
        checks=checks,
    )


@app.get("/metrics", tags=["system"])
async def prometheus_metrics() -> Response:
    """Prometheus-compatible metrics endpoint."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

app.include_router(feeds.router)
app.include_router(updates.router)
app.include_router(reports.router)
