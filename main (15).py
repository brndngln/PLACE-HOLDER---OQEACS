#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        CROSS-PROJECT LEARNING SERVICE                         ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This microservice ingests results from build pipelines and updates shared    ║
║ knowledge bases.  High-scoring builds contribute their successful patterns  ║
║ to the `proven_patterns` collection, while low-scoring builds contribute    ║
║ their failure cases to the `anti_patterns` collection.  Patterns are tagged  ║
║ with project identifiers so that projects can benefit from one another.      ║
║ The service also provides endpoints to query proven patterns across projects.║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import dataclasses
import os
from datetime import datetime
from typing import Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels


# ════════════════════════════════════════════════════════════════════
# DATA MODELS
# ════════════════════════════════════════════════════════════════════


class IngestRequest(BaseModel):
    """Input payload for ingesting pipeline results."""

    project: str = Field(..., description="Identifier of the project from which the result originates")
    score: float = Field(..., description="Weighted average score of the build")
    patterns: List[str] = Field(default_factory=list, description="Successful patterns extracted from the build")
    failures: List[str] = Field(default_factory=list, description="Failure descriptions extracted from the build")


class IngestResponse(BaseModel):
    status: str
    added_proven: int
    added_anti: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PatternEntry(BaseModel):
    project: str
    pattern: str


class PatternsResponse(BaseModel):
    status: str
    patterns: List[PatternEntry] = Field(default_factory=list)


# ════════════════════════════════════════════════════════════════════
# SERVICE IMPLEMENTATION
# ════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class CrossLearningService:
    """Service that routes patterns and failures based on score thresholds."""

    qdrant: AsyncQdrantClient
    proven_collection: str
    anti_collection: str
    high_threshold: float
    low_threshold: float
    logger: structlog.BoundLogger = dataclasses.field(init=False)
    ingest_counter: Counter = dataclasses.field(init=False)
    latency_histogram: Histogram = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.logger = structlog.get_logger(__name__).bind(component="cross_learning_service")
        self.ingest_counter = Counter(
            "cross_learning_ingest_total", "Total number of ingest operations"
        )
        self.latency_histogram = Histogram(
            "cross_learning_ingest_latency_seconds",
            "Latency of ingest operations",
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2),
        )

    async def ingest(self, req: IngestRequest) -> IngestResponse:
        self.ingest_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            added_proven = added_anti = 0
            import random
            import uuid
            # High score: proven patterns
            if req.score >= self.high_threshold:
                for pattern in req.patterns:
                    point_id = uuid.uuid4().hex
                    vector = [random.random() for _ in range(32)]
                    payload = {"pattern": pattern, "project": req.project}
                    try:
                        await self.qdrant.upsert(
                            collection_name=self.proven_collection,
                            points=[qmodels.PointStruct(id=point_id, vector=vector, payload=payload)],
                        )
                        added_proven += 1
                    except Exception as exc:  # noqa: B902
                        self.logger.error("proven_upsert_failed", pattern=pattern, error=str(exc))
            # Low score: anti patterns (failures)
            if req.score <= self.low_threshold:
                for failure in req.failures:
                    point_id = uuid.uuid4().hex
                    vector = [random.random() for _ in range(32)]
                    payload = {"description": failure, "category": "cross_learning", "tags": [req.project]}
                    try:
                        await self.qdrant.upsert(
                            collection_name=self.anti_collection,
                            points=[qmodels.PointStruct(id=point_id, vector=vector, payload=payload)],
                        )
                        added_anti += 1
                    except Exception as exc:  # noqa: B902
                        self.logger.error("anti_upsert_failed", failure=failure, error=str(exc))
            return IngestResponse(status="OK", added_proven=added_proven, added_anti=added_anti)

    async def get_proven_patterns(self, exclude_project: Optional[str], limit: int = 10) -> PatternsResponse:
        results: List[PatternEntry] = []
        try:
            offset = None
            fetched = 0
            while fetched < limit:
                points, offset = await self.qdrant.scroll(self.proven_collection, limit=64, offset=offset)
                for point in points:
                    payload = point.payload or {}
                    project = payload.get("project", "")
                    pattern = payload.get("pattern", "")
                    if exclude_project and project == exclude_project:
                        continue
                    results.append(PatternEntry(project=project, pattern=pattern))
                    fetched += 1
                    if fetched >= limit:
                        break
                if offset is None:
                    break
            return PatternsResponse(status="OK", patterns=results)
        except Exception as exc:  # noqa: B902
            self.logger.error("get_proven_patterns_failed", error=str(exc))
            raise HTTPException(status_code=500, detail="Failed to retrieve patterns")


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    qdrant_host = os.getenv("QDRANT_HOST", "omni-qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    proven_collection = os.getenv("PROVEN_COLLECTION", "proven_patterns")
    anti_collection = os.getenv("ANTI_COLLECTION", "anti_patterns")
    high_threshold = float(os.getenv("HIGH_SCORE_THRESHOLD", "9.0"))
    low_threshold = float(os.getenv("LOW_SCORE_THRESHOLD", "6.0"))
    service = CrossLearningService(
        qdrant=AsyncQdrantClient(host=qdrant_host, port=qdrant_port),
        proven_collection=proven_collection,
        anti_collection=anti_collection,
        high_threshold=high_threshold,
        low_threshold=low_threshold,
    )
    app = FastAPI(title="Cross Project Learning", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.post("/api/v1/ingest", response_model=IngestResponse)
    async def ingest_endpoint(request: IngestRequest) -> IngestResponse:
        return await service.ingest(request)

    @app.get("/api/v1/proven_patterns", response_model=PatternsResponse)
    async def proven_patterns_endpoint(exclude_project: Optional[str] = Query(None, description="Project to exclude"), limit: int = Query(10, ge=1, le=50)) -> PatternsResponse:
        return await service.get_proven_patterns(exclude_project, limit)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        try:
            await service.qdrant.get_collections()
        except Exception:
            raise HTTPException(status_code=503, detail="Qdrant unavailable")
        return {"status": "ready"}

    return app


app = create_app()