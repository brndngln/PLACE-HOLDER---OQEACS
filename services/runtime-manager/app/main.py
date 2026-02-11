"""
Omni Quantum Elite - Language Runtime Manager
System 4/14 - Generation Intelligence Layer

Production-ready microservice implementation for generation intelligence workflows.
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest

from app.config import settings
from app.database import check_database
from app.exceptions import ServiceError, exception_handlers
from app.routes import api

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(settings.log_level_int),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

SERVICE_INFO = Info("service", "Service metadata")
SERVICE_INFO.info({"name": settings.service_name, "version": settings.version, "tier": "generation-intelligence"})

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"])
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)
ACTIVE_REQUESTS = Gauge("http_requests_active", "Active requests")
ERROR_COUNT = Counter("http_errors_total", "Errors by type", ["error_type"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("service_starting", service=settings.service_name, version=settings.version, port=settings.service_port)
    yield
    logger.info("service_stopped", service=settings.service_name)


app = FastAPI(
    title=f"Omni Quantum Elite — {settings.service_name}",
    description="Language Runtime Manager",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
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
async def observability_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    task_id = request.headers.get("X-Task-ID", "")
    request.state.correlation_id = correlation_id
    request.state.task_id = task_id

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        task_id=task_id,
        method=request.method,
        path=request.url.path,
        service=settings.service_name,
    )

    ACTIVE_REQUESTS.inc()
    start = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed*1000:.2f}"
        if request.url.path not in ("/health", "/ready", "/metrics"):
            logger.info("request_completed", status=response.status_code, duration_ms=round(elapsed * 1000, 2))
        return response
    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - start
        ERROR_COUNT.labels(type(exc).__name__).inc()
        logger.error(
            "request_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=round(elapsed * 1000, 2),
        )
        raise
    finally:
        ACTIVE_REQUESTS.dec()


@app.get("/health", tags=["infra"], summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": settings.service_name, "version": settings.version}


@app.get("/ready", tags=["infra"], summary="Readiness probe")
async def readiness() -> JSONResponse:
    checks: dict[str, str] = {}
    healthy = True
    try:
        await check_database()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"
        healthy = False

    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", "service": settings.service_name, "checks": checks},
    )


@app.get("/metrics", tags=["infra"], summary="Prometheus metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/info", tags=["infra"], summary="Service metadata")
async def info() -> dict[str, Any]:
    return {
        "service": settings.service_name,
        "version": settings.version,
        "tier": "generation-intelligence",
        "phase": 1,
        "system_number": 4,
        "port": settings.service_port,
        "endpoints": sorted(
            set(
                route.path
                for route in app.routes
                if hasattr(route, "methods")
                and route.path
                not in ("/health", "/ready", "/metrics", "/info", "/docs", "/redoc", "/openapi.json")
            )
        ),
    }


app.include_router(api.router)
