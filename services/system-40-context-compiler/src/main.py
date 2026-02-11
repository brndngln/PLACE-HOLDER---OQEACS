"""System 40: Context Compiler — Assembles optimal token context for each LLM invocation."""
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
from src.routers import compile as compile_router
from src.routers import stats as stats_router
from src.routers import templates as templates_router
from src.services.compiler import ContextCompiler
from src.services.effectiveness import EffectivenessTracker
from src.services.embeddings import EmbeddingService
from src.services.qdrant_client import QdrantSearchService

logger = structlog.get_logger()
settings = Settings()

REQUEST_COUNT = Counter("requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("request_duration_seconds", "Request latency", ["method", "endpoint"])

_compiler: ContextCompiler | None = None
_effectiveness_tracker: EffectivenessTracker | None = None


def get_compiler() -> ContextCompiler | None:
    return _compiler


def get_effectiveness_tracker() -> EffectivenessTracker | None:
    return _effectiveness_tracker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _compiler, _effectiveness_tracker
    logger.info("starting", service=settings.SERVICE_NAME, port=settings.SERVICE_PORT)

    qdrant = QdrantSearchService(settings.QDRANT_URL)
    embeddings = EmbeddingService(settings.LITELLM_URL, settings.EMBEDDING_MODEL)
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    _compiler = ContextCompiler(
        qdrant=qdrant,
        embeddings=embeddings,
        redis_client=redis_client,
        settings=settings,
    )

    try:
        pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=2, max_size=10)
        _effectiveness_tracker = EffectivenessTracker(pool)
        logger.info("database_connected")
    except Exception as exc:
        logger.warning("database_connection_failed", error=str(exc))

    yield

    logger.info("shutting_down", service=settings.SERVICE_NAME)
    await qdrant.close()
    await redis_client.aclose()
    if _effectiveness_tracker and _effectiveness_tracker.pool:
        await _effectiveness_tracker.pool.close()


app = FastAPI(
    title="Omni Quantum Elite \u2014 System 40: Context Compiler",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(compile_router.router)
app.include_router(templates_router.router)
app.include_router(stats_router.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": settings.SERVICE_NAME, "version": "1.0.0"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
