#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        SPEC GENERATOR SERVICE                               ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This microservice implements spec‑driven development for the Omni Quantum   ║
║ platform. It accepts a task description and uses a local language model to   ║
║ generate a detailed technical specification in Markdown. The specification   ║
║ includes sections for requirements, data models, API endpoints, authentication║
║ flow, and error handling. After generation, the service calls the Code     ║
║ Scorer to evaluate the quality of the specification. If the score meets or  ║
║ exceeds the configured threshold, the spec is persisted into Qdrant for     ║
║ future retrieval and reference; otherwise, the spec is rejected.            ║
║                                                                              ║
║ The service exposes REST endpoints for generating specs, listing stored     ║
║ specs, and performing health and readiness checks. Prometheus metrics are   ║
║ provided via a `/metrics` endpoint.                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional

import structlog
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels


# ════════════════════════════════════════════════════════════════════
# Pydantic Models
# ════════════════════════════════════════════════════════════════════


class SpecRequest(BaseModel):
    """Input payload for generating a specification."""

    task: str = Field(..., description="Task description to be transformed into a spec")
    token_budget: Optional[int] = Field(
        None, description="Optional approximate token budget for the generated spec"
    )


class SpecResponse(BaseModel):
    """Response payload for spec generation."""

    status: str = Field(..., description="approved if stored, rejected otherwise")
    score: float = Field(..., description="Average score assigned by the Code Scorer")
    spec: str = Field(..., description="Markdown specification text")
    created_at: datetime = Field(..., description="Timestamp when the spec was generated")


class StoredSpec(BaseModel):
    id: str
    task: str
    spec: str
    score: float


class SpecsResponse(BaseModel):
    status: str
    specs: List[StoredSpec] = Field(default_factory=list)


# ════════════════════════════════════════════════════════════════════
# Repository Layer
# ════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class SpecRepository:
    """Repository for persisting specifications in Qdrant."""

    client: AsyncQdrantClient
    collection: str
    logger: structlog.BoundLogger = dataclasses.field(init=False)
    _initialized: bool = dataclasses.field(default=False, init=False)

    async def _ensure_collection(self) -> None:
        """Create the collection if it does not exist."""
        if self._initialized:
            return
        try:
            collections = await self.client.get_collections()
            names = [c.name for c in collections.collections]
            if self.collection not in names:
                # Create a simple vector collection using cosine distance; size 32 for random vectors
                await self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=qmodels.VectorParams(size=32, distance=qmodels.Distance.COSINE),
                )
            self._initialized = True
        except Exception as exc:  # noqa: B902
            self.logger.error("collection_init_failed", error=str(exc))
            raise

    async def insert(self, task: str, spec: str, score: float) -> None:
        """Insert a specification into the Qdrant collection."""
        await self._ensure_collection()
        # Use a random vector to enable basic similarity search; real embeddings can be
        # provided by an embedding model in the future.
        vector = [random.random() for _ in range(32)]
        payload = {
            "task": task,
            "spec": spec,
            "score": score,
            "created_at": datetime.utcnow().isoformat(),
        }
        point = qmodels.PointStruct(id=os.urandom(8).hex(), vector=vector, payload=payload)
        try:
            await self.client.upsert(self.collection, [point])
        except Exception as exc:  # noqa: B902
            self.logger.error("spec_upsert_failed", error=str(exc))
            raise

    async def list(self, limit: int = 10) -> List[StoredSpec]:
        """List stored specs without similarity search."""
        await self._ensure_collection()
        results: List[StoredSpec] = []
        try:
            offset = None
            fetched = 0
            while fetched < limit:
                points, offset = await self.client.scroll(self.collection, limit=64, offset=offset)
                for point in points:
                    payload = point.payload or {}
                    results.append(
                        StoredSpec(
                            id=str(point.id),
                            task=payload.get("task", ""),
                            spec=payload.get("spec", ""),
                            score=float(payload.get("score", 0.0)),
                        )
                    )
                    fetched += 1
                    if fetched >= limit:
                        break
                if offset is None:
                    break
            return results
        except Exception as exc:  # noqa: B902
            self.logger.error("spec_list_failed", error=str(exc))
            raise


# ════════════════════════════════════════════════════════════════════
# Service Layer
# ════════════════════════════════════════════════════════════════════


@dataclasses.dataclass
class SpecGenerationService:
    """Business logic for generating and persisting specifications."""

    repository: SpecRepository
    model_endpoint: str
    scorer_url: str
    score_threshold: float
    logger: structlog.BoundLogger = dataclasses.field(init=False)
    spec_counter: Counter = dataclasses.field(init=False)
    spec_histogram: Histogram = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.logger = structlog.get_logger(__name__).bind(component="spec_generation_service")
        self.spec_counter = Counter(
            "spec_generator_requests_total",
            "Total number of spec generation requests",
        )
        self.spec_histogram = Histogram(
            "spec_generator_latency_seconds",
            "Latency of spec generation requests",
            buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10),
        )

    async def generate(self, req: SpecRequest) -> SpecResponse:
        """Generate a specification, score it and optionally persist it."""
        timer = self.spec_histogram.time()
        self.spec_counter.inc()
        async with timer:
            # 1. Generate spec via local model
            spec_text = await self._request_spec(req)
            # 2. Score spec via code scorer service
            score = await self._score_spec(spec_text)
            status = "approved" if score >= self.score_threshold else "rejected"
            # 3. Persist if approved
            if status == "approved":
                await self.repository.insert(task=req.task, spec=spec_text, score=score)
            return SpecResponse(status=status, score=score, spec=spec_text, created_at=datetime.utcnow())

    async def _request_spec(self, req: SpecRequest) -> str:
        """Request the local LLM to produce a Markdown specification."""
        # Compose a system prompt instructing the model to produce a detailed
        # specification. The content should include multiple sections and
        # at least 10 API endpoints. We keep the temperature low for
        # determinism.
        system_prompt = (
            "You are a senior software architect. Given a project description, "
            "generate a detailed technical specification in Markdown. The specification "
            "must include the following sections:\n\n"
            "1. Requirements: enumerate functional and non‑functional requirements.\n"
            "2. Data Model: describe entities, attributes and relationships. Use tables or lists.\n"
            "3. API Endpoints: list at least 10 endpoints with HTTP method, path, parameters and response schema.\n"
            "4. Authentication Flow: explain how clients authenticate and authorize requests.\n"
            "5. Error Handling: define common error responses and codes.\n\n"
            "Return only valid JSON with a single key 'spec' whose value is the Markdown string."
        )
        payload = {
            "model": os.getenv("SPEC_MODEL", "local-omni-spec-generator"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.task},
            ],
            "temperature": 0.0,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.model_endpoint, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:  # noqa: B902
            self.logger.error("model_request_failed", error=str(exc))
            raise HTTPException(status_code=503, detail="Model service unavailable")
        # Extract spec from the returned content. The model response is expected
        # to return a choices list containing a message with JSON content.
        try:
            result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if isinstance(result, str):
                # Parse JSON from the model's response
                parsed = json.loads(result)
            else:
                parsed = result
            spec_text: str = parsed.get("spec", "")
        except Exception as exc:  # noqa: B902
            self.logger.error("model_parse_failed", error=str(exc), raw=data)
            raise HTTPException(status_code=500, detail="Invalid model response")
        return spec_text

    async def _score_spec(self, spec: str) -> float:
        """Call the Code Scorer service to score the spec."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.scorer_url, json={"code": spec}, timeout=30)
                resp.raise_for_status()
                result = resp.json()
        except Exception as exc:  # noqa: B902
            self.logger.error("scorer_request_failed", error=str(exc))
            raise HTTPException(status_code=503, detail="Scorer service unavailable")
        try:
            score = float(result.get("average", 0))
        except Exception:
            # Fallback: parse average from string
            score = float(str(result.get("average", "0")))
        return score


# ════════════════════════════════════════════════════════════════════
# Application Setup
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Read environment variables
    qdrant_host = os.getenv("QDRANT_HOST", "omni-qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("SPEC_COLLECTION", "specs")
    model_endpoint = os.getenv("MODEL_ENDPOINT", "http://omni-litellm:4000/v1/chat/completions")
    scorer_url = os.getenv("CODE_SCORER_URL", "http://code-scorer:8350/api/v1/score")
    score_threshold = float(os.getenv("SPEC_SCORE_THRESHOLD", "8.0"))

    repository = SpecRepository(client=AsyncQdrantClient(host=qdrant_host, port=qdrant_port), collection=collection)
    service = SpecGenerationService(
        repository=repository,
        model_endpoint=model_endpoint,
        scorer_url=scorer_url,
        score_threshold=score_threshold,
    )

    app = FastAPI(title="Spec Generator", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Mount metrics endpoint
    app.mount("/metrics", make_asgi_app())

    @app.post("/api/v1/generate", response_model=SpecResponse)
    async def generate_spec(req: SpecRequest) -> SpecResponse:
        return await service.generate(req)

    @app.get("/api/v1/specs", response_model=SpecsResponse)
    async def list_specs(limit: int = Query(10, ge=1, le=50)) -> SpecsResponse:
        specs = await repository.list(limit)
        return SpecsResponse(status="OK", specs=specs)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        try:
            # Ensure Qdrant is reachable and collection is initialized
            await repository._ensure_collection()
        except Exception:
            raise HTTPException(status_code=503, detail="Qdrant unavailable")
        return {"status": "ready"}

    return app