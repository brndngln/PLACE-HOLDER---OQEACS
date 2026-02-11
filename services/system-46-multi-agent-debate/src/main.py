"""System 46: Multi-Agent Debate Engine — FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

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
from src.routers import debate as debate_router
from src.routers import review as review_router
from src.services.debate_engine import DebateEngine

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

    engine = DebateEngine(settings=settings)
    debate_router.set_engine(engine)
    review_router.set_settings(settings)

    logger.info("debate_engine_ready", model=settings.DEFAULT_MODEL)

    yield

    logger.info("shutting_down", service=settings.SERVICE_NAME)


app = FastAPI(
    title="Omni Quantum Elite — System 46: Multi-Agent Debate Engine",
    description=(
        "Orchestrates multi-agent debates for coding tasks. Specialized AI "
        "agents (Architect, Implementer, Reviewer, Security, Performance) "
        "argue about the best approach before any code is written."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(debate_router.router)
app.include_router(review_router.router)


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
