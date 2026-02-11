"""System 47B: Semantic Code Understanding Engine."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from src.config import settings
from src.routers import analyze as analyze_router
from src.routers import impact as impact_router
from src.services.graph_builder import GraphBuilder
from src.services.impact_analyzer import ImpactAnalyzer
from src.services.meaning_extractor import MeaningExtractor
from src.services.parser import CodeParser

logger = structlog.get_logger(__name__)
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    parser = CodeParser()
    graph_builder = GraphBuilder(parser=parser)
    meaning = MeaningExtractor()
    impact = ImpactAnalyzer(graph_builder._graphs)

    analyze_router.wire(graph_builder, meaning)
    impact_router.wire(impact)
    logger.info("service_start", service=settings.SERVICE_NAME, port=settings.SERVICE_PORT)
    yield
    logger.info("service_stop", service=settings.SERVICE_NAME)


app = FastAPI(
    title="Omni Semantic Code Understanding",
    description="Deep semantic graphing and impact analysis for codebases.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(analyze_router.router)
app.include_router(impact_router.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": settings.SERVICE_NAME, "version": "1.0.0"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
