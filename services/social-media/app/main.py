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
from app.exceptions import exception_handlers
from app.routes import accounts, analytics, competitors, content, engagement, publishing, scheduling, strategy, trends

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
    title=f"Omni Quantum Elite - {settings.service_name}",
    description="Social media command center and growth intelligence",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

for exc_class, handler in exception_handlers.items():
    app.add_exception_handler(exc_class, handler)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    ACTIVE_REQUESTS.inc()
    start = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed*1000:.2f}"
        return response
    except Exception as exc:  # noqa: BLE001
        ERROR_COUNT.labels(type(exc).__name__).inc()
        raise exc
    finally:
        ACTIVE_REQUESTS.dec()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": settings.service_name, "version": settings.version}


@app.get("/ready")
async def ready() -> JSONResponse:
    checks = {}
    ok = True
    try:
        await check_database()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"
        ok = False
    return JSONResponse(status_code=200 if ok else 503, content={"status": "ready" if ok else "degraded", "checks": checks})


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/info")
async def info() -> dict[str, Any]:
    return {"service": settings.service_name, "version": settings.version, "tier": "generation-intelligence", "phase": 4, "system_number": 39, "port": 9641}


app.include_router(accounts.router)
app.include_router(content.router)
app.include_router(publishing.router)
app.include_router(scheduling.router)
app.include_router(trends.router)
app.include_router(competitors.router)
app.include_router(engagement.router)
app.include_router(analytics.router)
app.include_router(strategy.router)
