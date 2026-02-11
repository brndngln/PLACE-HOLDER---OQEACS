"""
System 42 — Agent Health Monitor  |  FastAPI application entry-point.

Lifecycle:
    1. Create asyncpg connection pool (best-effort — service runs
       degraded if Postgres is unavailable).
    2. Create Redis connection (best-effort).
    3. Instantiate the AgentHealthMonitor facade.
    4. Start the APScheduler background jobs.
    5. On shutdown, close pool + Redis + scheduler.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI, Response
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    generate_latest,
)

from src.config import settings
from src.routers import agents, drift, golden_tests, poison_pills
from src.services.health_monitor import AgentHealthMonitor
from src.services.scheduler import init_scheduler

# ── Structured logging setup ────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.get_level_from_name(settings.LOG_LEVEL),
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger("system42")

# ── Prometheus metrics ──────────────────────────────────────────────

REGISTRY = CollectorRegistry()
REQUEST_COUNT = Counter(
    "agent_health_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)
HEALTH_SCORE = Gauge(
    "agent_health_score",
    "Latest overall health score per agent",
    ["agent_id"],
    registry=REGISTRY,
)
UPTIME_GAUGE = Gauge(
    "agent_health_uptime_seconds",
    "Seconds since service started",
    registry=REGISTRY,
)

_start_time: datetime | None = None


# ── Lifespan ────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: set up and tear down shared resources."""
    global _start_time  # noqa: PLW0603
    _start_time = datetime.now(timezone.utc)

    # -- asyncpg pool (best-effort) -----------------------------------
    db_pool: Any | None = None
    try:
        import asyncpg  # noqa: F811

        dsn = settings.DATABASE_URL.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        db_pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
        logger.info("postgres_connected", dsn=dsn[:40] + "...")
    except Exception as exc:
        logger.warning("postgres_unavailable", error=str(exc))

    # -- Redis (best-effort) ------------------------------------------
    redis_client: Any | None = None
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
        await redis_client.ping()
        logger.info("redis_connected", url=settings.REDIS_URL)
    except Exception as exc:
        logger.warning("redis_unavailable", error=str(exc))
        redis_client = None

    # -- Monitor & scheduler ------------------------------------------
    monitor = AgentHealthMonitor(db_pool=db_pool)
    scheduler = init_scheduler(monitor)
    scheduler.start()
    logger.info("scheduler_started")

    # Store on app.state so routers can access them.
    app.state.db_pool = db_pool
    app.state.redis = redis_client
    app.state.monitor = monitor
    app.state.scheduler = scheduler

    logger.info(
        "system42_started",
        service=settings.SERVICE_NAME,
        port=settings.SERVICE_PORT,
    )

    yield  # ---- application runs here ----

    # -- Teardown -----------------------------------------------------
    scheduler.shutdown(wait=False)
    logger.info("scheduler_stopped")

    if redis_client is not None:
        await redis_client.aclose()
        logger.info("redis_disconnected")

    if db_pool is not None:
        await db_pool.close()
        logger.info("postgres_disconnected")

    logger.info("system42_stopped")


# ── Application factory ─────────────────────────────────────────────

app = FastAPI(
    title="System 42 — Agent Health Monitor",
    description=(
        "Poison-pill testing, golden-test suites, performance drift "
        "detection, A/B prompt testing, and agent benchmarking for "
        "the Omni Quantum Elite AI Coding System."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(agents.router)
app.include_router(poison_pills.router)
app.include_router(golden_tests.router)
app.include_router(drift.router)


# ── Core endpoints ──────────────────────────────────────────────────


@app.get("/health", tags=["infra"])
async def health_check() -> dict[str, Any]:
    """Liveness / readiness probe."""
    db_ok = False
    redis_ok = False

    if hasattr(app.state, "db_pool") and app.state.db_pool is not None:
        try:
            async with app.state.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_ok = True
        except Exception:
            pass

    if hasattr(app.state, "redis") and app.state.redis is not None:
        try:
            await app.state.redis.ping()
            redis_ok = True
        except Exception:
            pass

    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "postgres": "connected" if db_ok else "unavailable",
            "redis": "connected" if redis_ok else "unavailable",
        },
    }


@app.get("/metrics", tags=["infra"])
async def prometheus_metrics() -> Response:
    """Prometheus-compatible metrics scrape endpoint."""
    if _start_time is not None:
        elapsed = (datetime.now(timezone.utc) - _start_time).total_seconds()
        UPTIME_GAUGE.set(elapsed)

    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ── Dev entry-point ─────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
