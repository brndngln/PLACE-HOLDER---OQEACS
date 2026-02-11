"""System 43: Self-Testing System — Platform integration tests and health sweeps."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

from src.config import Settings
from src.routers import report as report_router
from src.routers import tests as tests_router
from src.services.scheduler import init_scheduler
from src.services.test_runner import TestRunner

logger = structlog.get_logger()
settings = Settings()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("starting", service=settings.SERVICE_NAME, port=settings.SERVICE_PORT)

    # -- Redis connection -----------------------------------------------------
    redis_client: aioredis.Redis | None = None
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("redis_connected")
    except Exception as exc:
        logger.warning("redis_connection_failed", error=str(exc))
        redis_client = None

    # -- Test runner -----------------------------------------------------------
    runner = TestRunner(settings=settings, redis_client=redis_client)

    # Wire runner into routers
    tests_router.set_runner(runner)
    report_router.set_runner(runner)

    # -- Scheduler ------------------------------------------------------------
    scheduler = init_scheduler(runner)
    scheduler.start()
    logger.info("scheduler_started", jobs=len(scheduler.get_jobs()))

    yield

    # -- Shutdown -------------------------------------------------------------
    logger.info("shutting_down", service=settings.SERVICE_NAME)
    scheduler.shutdown(wait=False)
    if redis_client is not None:
        await redis_client.aclose()


app = FastAPI(
    title="Omni Quantum Elite — System 43: Self-Testing System",
    description=(
        "Platform self-testing engine that runs integration tests against "
        "all Omni Quantum services to verify they are working correctly."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(tests_router.router)
app.include_router(report_router.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
    }


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
