from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from src.config import Settings
from src.routers import styles

settings = Settings()
logger = structlog.get_logger()
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("service_start", service=settings.SERVICE_NAME)
    yield
    logger.info("service_stop", service=settings.SERVICE_NAME)


app = FastAPI(title=settings.SERVICE_NAME, version="1.0.0", lifespan=lifespan)
app.include_router(styles.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
