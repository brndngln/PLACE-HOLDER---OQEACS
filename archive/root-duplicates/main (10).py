#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        MCP DOCUMENTATION SERVICE                             ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This microservice provides a Retrieval‑Augmented Generation (RAG) interface  ║
║ over a collection of framework documentation stored in Qdrant.  It exposes  ║
║ endpoints for searching documentation, retrieving API references, and        ║
║ fetching example usages.  Queries are matched using simple keyword filtering ║
║ against the payloads of the `framework_docs` collection.                    ║
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


# ════════════════════════════════════════════════════════════════════
# ENUMS AND DATA CLASSES
# ════════════════════════════════════════════════════════════════════


class DocStatus(str):
    """Enumeration of documentation retrieval statuses."""

    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class SearchDocsResponse(BaseModel):
    """Response model for documentation search."""

    status: DocStatus = Field(...)
    results: List[str] = Field(default_factory=list, description="List of documentation snippets")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ApiReferenceResponse(BaseModel):
    """Response model for API reference retrieval."""

    status: DocStatus = Field(...)
    reference: Optional[str] = Field(None, description="Detailed API reference documentation")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ExamplesResponse(BaseModel):
    """Response model for retrieving example code snippets."""

    status: DocStatus = Field(...)
    examples: List[str] = Field(default_factory=list, description="List of example code snippets")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ════════════════════════════════════════════════════════════════════
# SERVICE IMPLEMENTATION
# ════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class DocsService:
    """Business layer for documentation retrieval from Qdrant."""

    client: AsyncQdrantClient
    collection: str
    logger: structlog.BoundLogger = dataclasses.field(init=False)
    search_counter: Counter = dataclasses.field(init=False)
    search_latency: Histogram = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.logger = structlog.get_logger(__name__).bind(component="docs_service")
        self.search_counter = Counter(
            "mcp_docs_requests_total", "Total documentation search requests"
        )
        self.search_latency = Histogram(
            "mcp_docs_latency_seconds", "Documentation retrieval latency", buckets=(0.05, 0.1, 0.25, 0.5, 1, 2)
        )

    async def search_docs(self, query: str, limit: int = 5) -> SearchDocsResponse:
        self.search_counter.inc()
        timer = self.search_latency.time()
        async with timer:
            keywords = [kw.strip().lower() for kw in query.split() if len(kw) >= 3]
            if not keywords:
                return SearchDocsResponse(status=DocStatus.NOT_FOUND, results=[])
            results: List[str] = []
            try:
                offset = None
                while len(results) < limit:
                    points, offset = await self.client.scroll(self.collection, limit=64, offset=offset)
                    for point in points:
                        payload = point.payload or {}
                        content = payload.get("content", "")
                        if all(kw in content.lower() for kw in keywords):
                            results.append(content)
                            if len(results) >= limit:
                                break
                    if offset is None:
                        break
                status = DocStatus.FOUND if results else DocStatus.NOT_FOUND
                return SearchDocsResponse(status=status, results=results)
            except Exception as exc:  # noqa: B902
                self.logger.error("search_failed", error=str(exc))
                raise HTTPException(status_code=500, detail="Documentation search failed")

    async def get_api_reference(self, api_name: str) -> ApiReferenceResponse:
        self.search_counter.inc()
        timer = self.search_latency.time()
        async with timer:
            try:
                # API reference entries stored with payload type 'reference' keyed by 'api_name'
                offset = None
                while True:
                    points, offset = await self.client.scroll(self.collection, limit=64, offset=offset)
                    for point in points:
                        payload = point.payload or {}
                        if payload.get("type") == "reference" and payload.get("name", "").lower() == api_name.lower():
                            return ApiReferenceResponse(status=DocStatus.FOUND, reference=payload.get("content"))
                    if offset is None:
                        break
                return ApiReferenceResponse(status=DocStatus.NOT_FOUND, reference=None)
            except Exception as exc:  # noqa: B902
                self.logger.error("reference_failed", error=str(exc))
                raise HTTPException(status_code=500, detail="API reference lookup failed")

    async def get_examples(self, query: str, limit: int = 3) -> ExamplesResponse:
        self.search_counter.inc()
        timer = self.search_latency.time()
        async with timer:
            keywords = [kw.strip().lower() for kw in query.split() if len(kw) >= 3]
            if not keywords:
                return ExamplesResponse(status=DocStatus.NOT_FOUND, examples=[])
            examples: List[str] = []
            try:
                offset = None
                while len(examples) < limit:
                    points, offset = await self.client.scroll(self.collection, limit=64, offset=offset)
                    for point in points:
                        payload = point.payload or {}
                        if payload.get("type") != "example":
                            continue
                        content = payload.get("content", "")
                        if all(kw in content.lower() for kw in keywords):
                            examples.append(content)
                            if len(examples) >= limit:
                                break
                    if offset is None:
                        break
                status = DocStatus.FOUND if examples else DocStatus.NOT_FOUND
                return ExamplesResponse(status=status, examples=examples)
            except Exception as exc:  # noqa: B902
                self.logger.error("examples_failed", error=str(exc))
                raise HTTPException(status_code=500, detail="Example retrieval failed")


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    qdrant_host = os.getenv("QDRANT_HOST", "omni-qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("DOC_COLLECTION", "framework_docs")
    service = DocsService(client=AsyncQdrantClient(host=qdrant_host, port=qdrant_port), collection=collection)
    app = FastAPI(title="MCP Docs", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.get("/api/v1/search_docs", response_model=SearchDocsResponse)
    async def search_docs(query: str = Query(..., description="Search query"), limit: int = Query(5, ge=1, le=20)) -> SearchDocsResponse:
        return await service.search_docs(query, limit)

    @app.get("/api/v1/get_api_reference", response_model=ApiReferenceResponse)
    async def get_api_reference(api_name: str = Query(..., description="API or function name")) -> ApiReferenceResponse:
        return await service.get_api_reference(api_name)

    @app.get("/api/v1/get_examples", response_model=ExamplesResponse)
    async def get_examples(query: str = Query(..., description="Example search query"), limit: int = Query(3, ge=1, le=10)) -> ExamplesResponse:
        return await service.get_examples(query, limit)

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