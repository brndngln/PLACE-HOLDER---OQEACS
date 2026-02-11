#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ANTI-PATTERN KNOWLEDGE BASE SERVICE                       ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This service maintains a searchable repository of common anti‑patterns that   ║
║ agents should avoid.  Entries are stored in a Qdrant collection and can be    ║
║ retrieved by keywords or added dynamically when pipeline checks identify new   ║
║ issues.  It provides endpoints for querying and adding anti‑patterns, plus    ║
║ health, readiness, and metrics.                                              ║
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
# ENUMS AND DATA MODELS
# ════════════════════════════════════════════════════════════════════


class KBStatus(str):
    """Enumeration of knowledge base statuses."""

    OK = "OK"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class AntiPattern(BaseModel):
    """Model for an anti‑pattern entry."""

    description: str
    category: str
    tags: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    status: KBStatus
    results: List[AntiPattern] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class AddRequest(BaseModel):
    description: str
    category: str
    tags: List[str] = Field(default_factory=list)


class AddResponse(BaseModel):
    status: KBStatus
    id: Optional[str] = Field(None)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ════════════════════════════════════════════════════════════════════
# SERVICE IMPLEMENTATION
# ════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class AntiPatternService:
    """Service for querying and adding anti‑patterns in Qdrant."""

    client: AsyncQdrantClient
    collection: str
    logger: structlog.BoundLogger = dataclasses.field(init=False)
    request_counter: Counter = dataclasses.field(init=False)
    latency_histogram: Histogram = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.logger = structlog.get_logger(__name__).bind(component="anti_pattern_service")
        self.request_counter = Counter(
            "anti_pattern_requests_total", "Total anti‑pattern service requests"
        )
        self.latency_histogram = Histogram(
            "anti_pattern_latency_seconds",
            "Anti‑pattern service request latency",
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2),
        )

    async def search(self, query: str, limit: int = 5) -> SearchResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            keywords = [kw.strip().lower() for kw in query.split() if len(kw) >= 3]
            if not keywords:
                return SearchResponse(status=KBStatus.NOT_FOUND, results=[])
            results: List[AntiPattern] = []
            try:
                offset = None
                while len(results) < limit:
                    points, offset = await self.client.scroll(self.collection, limit=64, offset=offset)
                    for point in points:
                        payload = point.payload or {}
                        desc = payload.get("description", "")
                        category = payload.get("category", "")
                        tags = payload.get("tags", [])
                        content = " ".join([desc, category] + tags)
                        if all(kw in content.lower() for kw in keywords):
                            results.append(AntiPattern(description=desc, category=category, tags=tags))
                            if len(results) >= limit:
                                break
                    if offset is None:
                        break
                status = KBStatus.OK if results else KBStatus.NOT_FOUND
                return SearchResponse(status=status, results=results)
            except Exception as exc:  # noqa: B902
                self.logger.error("search_error", error=str(exc))
                raise HTTPException(status_code=500, detail="Search failed")

    async def add(self, description: str, category: str, tags: List[str]) -> AddResponse:
        self.request_counter.inc()
        timer = self.latency_histogram.time()
        async with timer:
            import uuid
            import random
            # ensure collection exists
            try:
                await self.client.get_collection(self.collection)
            except Exception:
                await self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=qmodels.VectorParams(size=32, distance=qmodels.Distance.COSINE),
                )
            point_id = uuid.uuid4().hex
            vector = [random.random() for _ in range(32)]
            payload = {"description": description, "category": category, "tags": tags}
            try:
                await self.client.upsert(
                    collection_name=self.collection,
                    points=[qmodels.PointStruct(id=point_id, vector=vector, payload=payload)],
                )
                return AddResponse(status=KBStatus.OK, id=point_id)
            except Exception as exc:  # noqa: B902
                self.logger.error("add_error", error=str(exc))
                raise HTTPException(status_code=500, detail="Failed to add anti‑pattern")


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    qdrant_host = os.getenv("QDRANT_HOST", "omni-qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("ANTI_COLLECTION", "anti_patterns")
    service = AntiPatternService(AsyncQdrantClient(host=qdrant_host, port=qdrant_port), collection)
    app = FastAPI(title="Anti Pattern Knowledge Base", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.get("/api/v1/search", response_model=SearchResponse)
    async def search_endpoint(query: str = Query(..., description="Keyword query"), limit: int = Query(5, ge=1, le=20)) -> SearchResponse:
        return await service.search(query, limit)

    @app.post("/api/v1/add", response_model=AddResponse)
    async def add_endpoint(request: AddRequest) -> AddResponse:
        return await service.add(request.description, request.category, request.tags)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        try:
            await service.client.get_collections()
        except Exception:
            raise HTTPException(status_code=503, detail="Qdrant unavailable")
        return {"status": "ready"}

    return app


app = create_app()