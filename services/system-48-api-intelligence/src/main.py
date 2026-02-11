"""System 48B: Real-Time API Intelligence service."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from src.config import settings
from src.routers import scan as scan_router
from src.routers import upgrades as upgrades_router
from src.services.scheduler import create_scheduler

logger = structlog.get_logger(__name__)
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("service_start", service=settings.SERVICE_NAME, port=settings.SERVICE_PORT)
    yield
    scheduler.shutdown(wait=False)
    logger.info("service_stop", service=settings.SERVICE_NAME)


app = FastAPI(
    title="Omni API Intelligence",
    description="Real-time dependency/API intelligence, compatibility checks and upgrade planning.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(scan_router.router)
app.include_router(upgrades_router.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": settings.SERVICE_NAME, "version": "1.0.0"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
