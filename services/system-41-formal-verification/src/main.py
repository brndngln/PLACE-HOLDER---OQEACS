"""System 41: Formal Verification Engine — Mathematical proof of code correctness."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from src.config import Settings
from src.routers import specs as specs_router
from src.routers import verify as verify_router
from src.services.spec_generator import SpecGenerator
from src.services.verifier import VerificationService

logger = structlog.get_logger()
settings = Settings()

REQUEST_COUNT = Counter("requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("request_duration_seconds", "Request latency", ["method", "endpoint"])
VERIFICATIONS_TOTAL = Counter("verifications_total", "Total verifications", ["tool", "status"])

_verifier: VerificationService | None = None
_spec_generator: SpecGenerator | None = None


def get_verifier() -> VerificationService | None:
    return _verifier


def get_spec_generator() -> SpecGenerator | None:
    return _spec_generator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _verifier, _spec_generator
    logger.info("starting", service=settings.SERVICE_NAME, port=settings.SERVICE_PORT)

    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    pool: asyncpg.Pool | None = None
    try:
        pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=2, max_size=10)
        logger.info("database_connected")
    except Exception as exc:
        logger.warning("database_connection_failed", error=str(exc))

    _verifier = VerificationService(pool=pool, redis_client=redis_client, settings=settings)
    _spec_generator = SpecGenerator(settings=settings)

    yield

    logger.info("shutting_down", service=settings.SERVICE_NAME)
    await redis_client.aclose()
    if pool:
        await pool.close()


app = FastAPI(
    title="Omni Quantum Elite \u2014 System 41: Formal Verification Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(verify_router.router)
app.include_router(specs_router.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": settings.SERVICE_NAME, "version": "1.0.0"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
