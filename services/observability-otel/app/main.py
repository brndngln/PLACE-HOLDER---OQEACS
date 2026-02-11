from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from app.config import settings
from app.exceptions import exception_handlers
from app.routes.api import bind_routes, router
from app.services.core import ObservabilityCore

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(settings.log_level_int),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

REQUEST_COUNT = Counter("observability_otel_http_requests_total", "HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("observability_otel_http_request_duration_seconds", "Request duration", ["method", "path"])
ACTIVE_REQUESTS = Gauge("observability_otel_http_requests_active", "Active requests")
INSTRUMENTATION_CHECKS = Counter("observability_otel_instrumentation_checks_total", "Instrumentation checks", ["status"])

core = ObservabilityCore(settings.data_path, settings.otel_collector_url, settings.default_sampling_ratio)
bind_routes(core)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await core.initialize()
    logger.info("service_starting", service=settings.service_name, port=settings.service_port)
    yield
    logger.info("service_stopped", service=settings.service_name)


app = FastAPI(
    title="Omni Quantum Elite - Observability OTel",
    version="1.0.0",
    description="OpenTelemetry instrumentation and collector control plane",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for exc_class, handler in exception_handlers.items():
    app.add_exception_handler(exc_class, handler)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id, path=request.url.path)
    ACTIVE_REQUESTS.inc()
    start = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        REQUEST_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    finally:
        ACTIVE_REQUESTS.dec()


@app.get("/health", tags=["infra"])
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": settings.service_name}


@app.get("/ready", tags=["infra"])
async def ready() -> JSONResponse:
    collector = await core.collector_status()
    if collector.healthy:
        return JSONResponse(status_code=200, content={"status": "ready", "checks": {"collector": "ok"}})
    return JSONResponse(status_code=503, content={"status": "degraded", "checks": {"collector": collector.detail}})


@app.get("/metrics", tags=["infra"])
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/info", tags=["infra"])
async def info() -> dict[str, str | int]:
    return {
        "service": settings.service_name,
        "port": settings.service_port,
        "collector": settings.otel_collector_url,
    }


app.include_router(router)
