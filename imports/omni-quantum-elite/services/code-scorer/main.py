#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                               CODE SCORER                                    ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This module implements the Code Scorer service for the Omni Quantum platform.║
║ It exposes a REST API for scoring source code across ten distinct quality    ║
║ dimensions using a local LLM via LiteLLM, persists scores into Qdrant and    ║
║ provides health, readiness and metrics endpoints.                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

The service adheres to the architecture patterns defined in CODE‑DNA.md.
It separates concerns into repository and service layers, uses dataclasses
for internal models and Pydantic for request/response models. Logging is
implemented with structlog emitting JSON. Metrics are exposed via the
Prometheus client. All external connections use container names defined in
inter‑service environment variables.
"""

from __future__ import annotations

import asyncio
import dataclasses
import enum
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams
import httpx

# ════════════════════════════════════════════════════════════════════
# ENUMS AND DATA MODELS
# ════════════════════════════════════════════════════════════════════


class Dimension(str, enum.Enum):
    """Enumeration of scoring dimensions."""

    CORRECTNESS = "correctness"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ERROR_HANDLING = "error_handling"
    READABILITY = "readability"
    TESTABILITY = "testability"
    API_DESIGN = "api_design"
    OBSERVABILITY = "observability"
    DOCUMENTATION = "documentation"
    STANDARDS = "standards"


@dataclasses.dataclass
class ScoreRecord:
    """Internal model representing a scored code snippet."""

    id: str
    code: str
    scores: Dict[Dimension, int]
    average: Decimal
    feedback: str
    created_at: datetime


# ════════════════════════════════════════════════════════════════════
# Pydantic Models
# ════════════════════════════════════════════════════════════════════


class ScoreRequest(BaseModel):
    """Schema for incoming score requests."""

    code: str = Field(..., description="Source code to evaluate")


class ScoreResponse(BaseModel):
    """Schema for score responses."""

    id: str = Field(..., description="Identifier of the score record")
    scores: Dict[Dimension, int] = Field(..., description="Per‑dimension scores")
    average: Decimal = Field(..., description="Weighted average score")
    feedback: str = Field(..., description="Model feedback on the code")
    created_at: datetime = Field(..., description="Timestamp of record creation")


# ════════════════════════════════════════════════════════════════════
# REPOSITORY LAYER
# ════════════════════════════════════════════════════════════════════


class CodeScoreRepository:
    """Repository layer for persisting and retrieving score records in Qdrant."""

    COLLECTION_NAME = "code_scores"

    def __init__(self, qdrant_host: str, qdrant_port: int) -> None:
        self._client = AsyncQdrantClient(host=qdrant_host, port=qdrant_port)
        self._initialized: bool = False
        self._logger = structlog.get_logger(__name__).bind(component="repo")

    async def _ensure_collection(self) -> None:
        """Ensure the collection exists in Qdrant."""
        if self._initialized:
            return
        try:
            collections = await self._client.get_collections()
            names = [c.name for c in collections.collections]
            if self.COLLECTION_NAME not in names:
                await self._client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(size=10, distance=Distance.COSINE),
                )
            self._initialized = True
        except Exception as exc:  # noqa: B902
            self._logger.error("collection_init_failed", error=str(exc))
            raise

    async def insert(self, record: ScoreRecord) -> None:
        """Insert a new score record into Qdrant."""
        await self._ensure_collection()
        # Convert scores to vector in order of Dimension enum
        vector = [float(record.scores.get(dim, 0)) for dim in Dimension]
        metadata = {
            "id": record.id,
            "average": str(record.average),
            "feedback": record.feedback,
            "created_at": record.created_at.isoformat(),
        }
        point = PointStruct(id=record.id, vector=vector, payload=metadata)
        try:
            await self._client.upsert(self.COLLECTION_NAME, [point])
        except Exception as exc:  # noqa: B902
            self._logger.error("upsert_failed", error=str(exc))
            raise


# ════════════════════════════════════════════════════════════════════
# SERVICE LAYER
# ════════════════════════════════════════════════════════════════════


class CodeScoringService:
    """Business logic for scoring code and persisting results."""

    def __init__(self, repo: CodeScoreRepository, model_endpoint: str) -> None:
        self._repo = repo
        self._model_endpoint = model_endpoint
        self._logger = structlog.get_logger(__name__).bind(component="service")
        # Metrics
        self._score_counter = Counter(
            "code_scorer_requests_total",
            "Total number of code scoring requests",
        )
        self._score_histogram = Histogram(
            "code_scorer_latency_seconds",
            "Latency of code scoring requests",
            buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10),
        )

    async def score(self, code: str) -> ScoreRecord:
        """Score the provided code and persist the result."""
        timer = self._score_histogram.time()
        self._score_counter.inc()
        async with timer:
            # Request model scoring
            scores, feedback = await self._request_model_scores(code)
            # Compute weighted average (equal weight)
            average = Decimal(sum(scores.values())) / Decimal(len(scores))
            record = ScoreRecord(
                id=self._generate_id(),
                code=code,
                scores=scores,
                average=average.quantize(Decimal("0.01")),
                feedback=feedback,
                created_at=datetime.utcnow(),
            )
            # Persist to repository
            await self._repo.insert(record)
            return record

    async def _request_model_scores(self, code: str) -> (Dict[Dimension, int], str):
        """Call the local LLM via LiteLLM to obtain scores and feedback."""
        payload = {
            "model": "local-omni-code-scorer",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a code quality evaluator. Score the code across ten dimensions (correctness, security, performance, error_handling, readability, testability, api_design, observability, documentation, standards) on a scale from 0 to 10 and provide concise feedback.",
                },
                {"role": "user", "content": code},
            ],
            "temperature": 0.0,
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self._model_endpoint, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: B902
            self._logger.error("model_request_failed", error=str(exc))
            raise HTTPException(status_code=503, detail="Model service unavailable")
        # Expect the model to return JSON with scores and feedback
        try:
            result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = result
            if isinstance(parsed, str):
                import json

                parsed = json.loads(parsed)
            scores: Dict[Dimension, int] = {Dimension(k): int(v) for k, v in parsed["scores"].items()}
            feedback: str = str(parsed.get("feedback", ""))
        except Exception as exc:  # noqa: B902
            self._logger.error("model_parse_failed", error=str(exc), raw=data)
            raise HTTPException(status_code=500, detail="Invalid model response")
        return scores, feedback

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique identifier using timestamp and randomness."""
        import uuid

        return uuid.uuid4().hex


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    logger = structlog.get_logger(__name__).bind(component="app")
    qdrant_host = os.getenv("QDRANT_HOST", "omni-qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    model_endpoint = os.getenv("MODEL_ENDPOINT", "http://omni-litellm:4000/v1/chat/completions")

    repo = CodeScoreRepository(qdrant_host=qdrant_host, qdrant_port=qdrant_port)
    service = CodeScoringService(repo=repo, model_endpoint=model_endpoint)

    app = FastAPI(title="Code Scorer", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.post("/api/v1/score", response_model=ScoreResponse)
    async def score_endpoint(request: ScoreRequest) -> ScoreResponse:
        """Score the provided code snippet and return the results."""
        record = await service.score(request.code)
        return ScoreResponse(
            id=record.id,
            scores=record.scores,
            average=record.average,
            feedback=record.feedback,
            created_at=record.created_at,
        )

    @app.get("/health")
    async def health() -> Dict[str, str]:
        """Simple health endpoint."""
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        """Readiness probe."""
        try:
            await repo._ensure_collection()
        except Exception:
            logger.warning("qdrant_not_ready")
            raise HTTPException(status_code=503, detail="Dependencies not ready")
        return {"status": "ready"}

    return app


app = create_app()