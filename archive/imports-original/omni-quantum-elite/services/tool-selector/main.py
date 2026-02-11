#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        TOOL SELECTION SERVICE                                ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This microservice assists agent workflows by recommending the most relevant  ║
║ development tools for a given task description.  It maintains a Qdrant      ║
║ collection of tool descriptions and uses simple keyword filtering to select  ║
║ the top N tools matching the user's intent.  It provides endpoints for      ║
║ selecting tools and exposes standard health, readiness and metrics routes.  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
import re
import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
from qdrant_client import AsyncQdrantClient


# ════════════════════════════════════════════════════════════════════
# ENUMS AND DATA CLASSES
# ════════════════════════════════════════════════════════════════════


class SelectionStatus(str):
    """Enumeration of result statuses."""

    SUCCESS = "SUCCESS"
    NO_MATCH = "NO_MATCH"
    ERROR = "ERROR"


@dataclasses.dataclass
class ToolRecord:
    """Internal representation of a tool entry."""

    id: uuid.UUID
    name: str
    description: str
    created_at: datetime = dataclasses.field(default_factory=datetime.utcnow)


class ToolSelectRequest(BaseModel):
    """Incoming request for tool selection."""

    task_description: str = Field(..., description="Natural language description of the task")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Maximum number of tools to return")


class ToolSelectResponse(BaseModel):
    """Response containing selected tools."""

    status: SelectionStatus = Field(..., description="Selection outcome status")
    tools: List[dict] = Field(default_factory=list, description="List of selected tool records")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when selection was generated")


# ════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ════════════════════════════════════════════════════════════════════


def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """Simple keyword extraction based on word length and uniqueness."""
    words = re.findall(r"\b\w{4,}\b", text.lower())
    unique = list(dict.fromkeys(words))
    return unique[:max_keywords]


# ════════════════════════════════════════════════════════════════════
# SERVICE IMPLEMENTATION
# ════════════════════════════════════════════════════════════════════


class ToolSelectorService:
    """Business logic for selecting relevant tools from Qdrant."""

    def __init__(self, host: str, port: int, collection: str) -> None:
        self.client = AsyncQdrantClient(host=host, port=port)
        self.collection = collection
        self.logger = structlog.get_logger(__name__).bind(component="tool_selector_service")
        self.request_count = Counter(
            "tool_selector_requests_total", "Total tool selection requests"
        )
        self.request_latency = Histogram(
            "tool_selector_latency_seconds",
            "Tool selection latency in seconds",
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2),
        )

    async def select_tools(self, task_description: str, top_k: int) -> ToolSelectResponse:
        self.request_count.inc()
        timer = self.request_latency.time()
        async with timer:
            keywords = extract_keywords(task_description)
            try:
                tools = await self._search_qdrant(keywords, top_k)
                status = SelectionStatus.SUCCESS if tools else SelectionStatus.NO_MATCH
                return ToolSelectResponse(status=status, tools=tools)
            except Exception as exc:  # noqa: B902
                self.logger.error("selection_failed", error=str(exc))
                raise HTTPException(status_code=500, detail="Tool selection failed")

    async def _search_qdrant(self, keywords: List[str], limit: int) -> List[dict]:
        """Perform a simple keyword search over tool descriptions in Qdrant."""
        results: List[dict] = []
        offset = None
        fetched = 0
        try:
            while fetched < limit:
                points, offset = await self.client.scroll(self.collection, limit=64, offset=offset)
                for point in points:
                    payload = point.payload or {}
                    name = payload.get("name", "")
                    description = payload.get("description", "")
                    content = f"{name} {description}"
                    if all(kw.lower() in content.lower() for kw in keywords):
                        results.append({"name": name, "description": description})
                        fetched += 1
                        if fetched >= limit:
                            break
                if offset is None:
                    break
        except Exception as exc:  # noqa: B902
            self.logger.warning("qdrant_search_error", error=str(exc))
        return results


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    """Initialize the FastAPI application and routes."""
    qdrant_host = os.getenv("QDRANT_HOST", "omni-qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("TOOL_COLLECTION", "tool_descriptions")
    service = ToolSelectorService(qdrant_host, qdrant_port, collection)
    app = FastAPI(title="Tool Selector", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.post("/api/v1/select", response_model=ToolSelectResponse)
    async def select_endpoint(request: ToolSelectRequest) -> ToolSelectResponse:
        return await service.select_tools(request.task_description, request.top_k or 5)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> dict:
        # Check connectivity to Qdrant
        try:
            await service.client.get_collections()
        except Exception:
            raise HTTPException(status_code=503, detail="Qdrant unavailable")
        return {"status": "ready"}

    return app


app = create_app()