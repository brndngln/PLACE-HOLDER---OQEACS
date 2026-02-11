#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          SEMANTIC INTENT VERIFIER                           ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This service compares a specification against source code using a distinct  ║
║ language model to detect mismatches in intent, helping to catch correlated   ║
║ hallucinations where the implementation diverges from the stated design.    ║
╚══════════════════════════════════════════════════════════════════════════════╝

It provides a REST API that accepts a spec and code, queries a local LLM via
the Ollama bridge and returns whether the code fulfills the spec along with
identified issues and a confidence score. It follows Omni's service patterns
with JSON logging, metrics and health endpoints.
"""

from __future__ import annotations

import enum
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, make_asgi_app
import httpx

# ════════════════════════════════════════════════════════════════════
# ENUMS AND DATA MODELS
# ════════════════════════════════════════════════════════════════════


class IntentMatch(str, enum.Enum):
    """Enumeration of intent verification results."""

    MATCH = "MATCH"
    MISMATCH = "MISMATCH"


class IntentRequest(BaseModel):
    """Request payload for intent verification."""

    spec: str = Field(..., description="Formal specification of expected behaviour")
    code: str = Field(..., description="Implementation source code to verify")


class IntentResponse(BaseModel):
    """Response payload for intent verification."""

    result: IntentMatch = Field(..., description="Whether code matches spec")
    issues: List[str] = Field(..., description="List of mismatches identified")
    confidence: Decimal = Field(..., description="Confidence score between 0 and 1")
    evaluated_at: datetime = Field(..., description="Timestamp of evaluation")


# ════════════════════════════════════════════════════════════════════
# SERVICE LAYER
# ════════════════════════════════════════════════════════════════════


class IntentVerifierService:
    """Service that delegates comparison to a local language model."""

    def __init__(self, model_endpoint: str) -> None:
        self._model_endpoint = model_endpoint
        self._logger = structlog.get_logger(__name__).bind(component="intent_verifier_service")
        self._counter = Counter(
            "intent_verifier_requests_total",
            "Total number of intent verification requests",
        )
        self._histogram = Histogram(
            "intent_verifier_latency_seconds",
            "Latency of intent verification requests",
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
        )

    async def verify(self, spec: str, code: str) -> IntentResponse:
        timer = self._histogram.time()
        self._counter.inc()
        async with timer:
            payload = {
                "model": "local-omni-intent-verifier",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a code intent verifier. Compare the given spec and code."
                            " Respond in JSON with fields: result ('MATCH' or 'MISMATCH'),"
                            " issues (list of strings explaining mismatches) and confidence"
                            " (0-1)."
                        ),
                    },
                    {"role": "user", "content": f"Spec:\n{spec}\n\nCode:\n{code}"},
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
            try:
                result_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if isinstance(result_content, str):
                    import json

                    parsed = json.loads(result_content)
                else:
                    parsed = result_content
                result = IntentMatch(parsed.get("result", "MISMATCH"))
                issues = [str(i) for i in parsed.get("issues", [])]
                confidence = Decimal(str(parsed.get("confidence", 0.0)))
            except Exception as exc:  # noqa: B902
                self._logger.error("model_parse_failed", error=str(exc), raw=data)
                raise HTTPException(status_code=500, detail="Invalid model response")
            return IntentResponse(
                result=result,
                issues=issues,
                confidence=confidence.quantize(Decimal("0.01")),
                evaluated_at=datetime.utcnow(),
            )


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    model_endpoint = os.getenv("MODEL_ENDPOINT", "http://omni-ollama:11434/api/chat")
    service = IntentVerifierService(model_endpoint=model_endpoint)
    logger = structlog.get_logger(__name__).bind(component="intent_verifier_app")

    app = FastAPI(title="Intent Verifier", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.post("/api/v1/verify-intent", response_model=IntentResponse)
    async def verify_intent_endpoint(request: IntentRequest) -> IntentResponse:
        return await service.verify(request.spec, request.code)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        # Ready if able to hit model endpoint
        try:
            async with httpx.AsyncClient() as client:
                await client.post(model_endpoint, json={}, timeout=5)
        except Exception:
            logger.warning("model_unavailable")
            raise HTTPException(status_code=503, detail="Model endpoint unavailable")
        return {"status": "ready"}

    return app


app = create_app()