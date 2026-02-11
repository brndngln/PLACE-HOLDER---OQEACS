'''omni-buildgraph-planner service entrypoint.'''
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import Depends, FastAPI, Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from src.config import Settings
from src.dependencies import get_service
from src.service import OmniService


structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()
settings = Settings()

REQUEST_COUNT = Counter(
    "omni_buildgraph_planner_requests_total",
    "Total requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "omni_buildgraph_planner_request_seconds",
    "Request latency",
    ["method", "endpoint"],
)

ENDPOINTS: list[dict[str, str]] = [{"method": "POST", "path": "/api/v1/graph/analyze", "operation": "graph_analyze_post"}, {"method": "POST", "path": "/api/v1/graph/affected", "operation": "graph_affected_post"}, {"method": "POST", "path": "/api/v1/graph/generate-build-files", "operation": "graph_generate_build_files_post"}]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("service_starting", service=settings.service_name, port=settings.port)
    app.state.service = await OmniService.create(settings.service_name)
    yield
    await app.state.service.shutdown()
    logger.info("service_stopped", service=settings.service_name)


app = FastAPI(title="omni-buildgraph-planner", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    REQUEST_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
    return response


def make_handler(operation: str):
    async def handler(request: Request, service: OmniService = Depends(get_service)) -> dict[str, Any]:
        payload: dict[str, Any] = dict(request.query_params)
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                json_body = await request.json()
                if isinstance(json_body, dict):
                    payload.update(json_body)
            except Exception:
                pass
        result = await service.handle(
            operation=operation,
            payload=payload,
            path_params=dict(request.path_params),
        )
        return result

    return handler


for endpoint in ENDPOINTS:
    app.add_api_route(
        endpoint["path"],
        make_handler(endpoint["operation"]),
        methods=[endpoint["method"]],
        tags=["api"],
        operation_id=endpoint["operation"],
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": settings.service_name, "version": "1.0.0"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
