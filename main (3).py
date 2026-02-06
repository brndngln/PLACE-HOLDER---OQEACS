#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                             QUALITY GATE ENGINE                              ║
╟──────────────────────────────────────────────────────────────────────────────╢
║ This microservice implements a quality gate that evaluates code quality      ║
║ metrics against configurable thresholds and returns a binary PASS/FAIL       ║
║ decision accompanied by actionable fix messages.                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

The service exposes a REST API for pipeline integrations. It evaluates
coverage, cyclomatic complexity, lint warnings and other metrics provided
in the request against thresholds configured via environment variables. It
uses structlog for JSON logging, exposes Prometheus metrics and provides
/health, /ready and /metrics endpoints.
"""

from __future__ import annotations

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

# ════════════════════════════════════════════════════════════════════
# ENUMS AND DATA MODELS
# ════════════════════════════════════════════════════════════════════


class EvaluationResult(str, enum.Enum):
    """Enumeration of evaluation outcomes."""

    PASS = "PASS"
    FAIL = "FAIL"


class EvaluateRequest(BaseModel):
    """Request schema for quality evaluation."""

    coverage: Decimal = Field(..., ge=0, le=100, description="Test coverage percentage")
    complexity: Decimal = Field(..., ge=0, description="Average cyclomatic complexity")
    lint_errors: int = Field(..., ge=0, description="Number of lint violations")
    secret_issues: int = Field(..., ge=0, description="Number of secret scanning findings")
    dependency_issues: int = Field(..., ge=0, description="Number of dependency issues")


class EvaluateResponse(BaseModel):
    """Response schema for quality evaluation."""

    result: EvaluationResult = Field(..., description="PASS or FAIL")
    messages: List[str] = Field(..., description="Fix instructions for failing checks")
    evaluated_at: datetime = Field(..., description="Timestamp of evaluation")


# ════════════════════════════════════════════════════════════════════
# SERVICE LAYER
# ════════════════════════════════════════════════════════════════════


class QualityGateService:
    """Business logic to evaluate metrics against thresholds."""

    def __init__(self) -> None:
        # Read thresholds from environment or default values
        self.coverage_threshold = Decimal(os.getenv("COVERAGE_THRESHOLD", "80"))
        self.complexity_threshold = Decimal(os.getenv("COMPLEXITY_THRESHOLD", "15"))
        self.lint_errors_threshold = int(os.getenv("LINT_ERRORS_THRESHOLD", "0"))
        self.secret_issues_threshold = int(os.getenv("SECRET_ISSUES_THRESHOLD", "0"))
        self.dependency_issues_threshold = int(os.getenv("DEPENDENCY_ISSUES_THRESHOLD", "0"))
        self._logger = structlog.get_logger(__name__).bind(component="quality_gate_service")
        # Metrics
        self._eval_counter = Counter(
            "quality_gate_requests_total",
            "Total number of quality gate evaluations",
        )
        self._eval_histogram = Histogram(
            "quality_gate_latency_seconds",
            "Latency of quality gate evaluations",
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
        )

    async def evaluate(self, metrics: EvaluateRequest) -> EvaluateResponse:
        """Evaluate the provided metrics against configured thresholds."""
        timer = self._eval_histogram.time()
        self._eval_counter.inc()
        messages: List[str] = []
        result = EvaluationResult.PASS
        async with timer:
            # Coverage check
            if metrics.coverage < self.coverage_threshold:
                result = EvaluationResult.FAIL
                messages.append(
                    f"Increase test coverage from {metrics.coverage}% to at least {self.coverage_threshold}%"
                )
            # Complexity check
            if metrics.complexity > self.complexity_threshold:
                result = EvaluationResult.FAIL
                messages.append(
                    f"Reduce average cyclomatic complexity from {metrics.complexity} to below {self.complexity_threshold}"
                )
            # Lint errors
            if metrics.lint_errors > self.lint_errors_threshold:
                result = EvaluationResult.FAIL
                messages.append(
                    f"Resolve {metrics.lint_errors} lint violation(s); limit is {self.lint_errors_threshold}"
                )
            # Secrets
            if metrics.secret_issues > self.secret_issues_threshold:
                result = EvaluationResult.FAIL
                messages.append(
                    f"Remove {metrics.secret_issues} secret issue(s); none allowed"
                )
            # Dependency issues
            if metrics.dependency_issues > self.dependency_issues_threshold:
                result = EvaluationResult.FAIL
                messages.append(
                    f"Fix {metrics.dependency_issues} dependency issue(s); none allowed"
                )
            return EvaluateResponse(
                result=result,
                messages=messages,
                evaluated_at=datetime.utcnow(),
            )


# ════════════════════════════════════════════════════════════════════
# APPLICATION SETUP
# ════════════════════════════════════════════════════════════════════


def create_app() -> FastAPI:
    service = QualityGateService()
    logger = structlog.get_logger(__name__).bind(component="quality_gate_app")
    app = FastAPI(title="Quality Gate Engine", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Mount metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.post("/api/v1/evaluate", response_model=EvaluateResponse)
    async def evaluate_endpoint(request: EvaluateRequest) -> EvaluateResponse:
        """Evaluate code quality metrics and return pass/fail with messages."""
        return await service.evaluate(request)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> Dict[str, str]:
        # Always ready since no external dependencies
        return {"status": "ready"}

    return app


app = create_app()