"""System 49: Execution Verification Loop — FastAPI application entry point."""

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
from src.routers import tests as tests_router
from src.routers import verify as verify_router
from src.services.sandbox import SandboxExecutor
from src.services.test_runner import TestRunner
from src.services.verifier import VerificationLoop

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
    """Application startup / shutdown lifecycle."""
    logger.info("starting", service=settings.SERVICE_NAME, port=settings.SERVICE_PORT)

    # -- Redis connection --------------------------------------------------
    redis_client: aioredis.Redis | None = None
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("redis_connected")
    except Exception as exc:
        logger.warning("redis_connection_failed", error=str(exc))
        redis_client = None

    # -- Service wiring ----------------------------------------------------
    sandbox = SandboxExecutor(settings=settings)
    test_runner = TestRunner(settings=settings, sandbox=sandbox)
    verifier = VerificationLoop(
        settings=settings,
        sandbox=sandbox,
        test_runner=test_runner,
        redis_client=redis_client,
    )

    # Wire services into routers
    verify_router.set_services(verifier=verifier, sandbox=sandbox, redis_client=redis_client)
    tests_router.set_test_runner(test_runner)

    logger.info("services_initialized")

    yield

    # -- Shutdown ----------------------------------------------------------
    logger.info("shutting_down", service=settings.SERVICE_NAME)
    if redis_client is not None:
        await redis_client.aclose()


app = FastAPI(
    title="Omni Quantum Elite \u2014 System 49: Execution Verification Loop",
    description=(
        "Every piece of AI-generated code gets EXECUTED in a sandbox before being "
        "committed. If it fails, the error is fed back to the AI for regeneration. "
        "Only code that ACTUALLY RUNS gets shipped."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(verify_router.router)
app.include_router(tests_router.router)


# ------------------------------------------------------------------
# Health & metrics
# ------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness / readiness probe."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
    }


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus-compatible metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
