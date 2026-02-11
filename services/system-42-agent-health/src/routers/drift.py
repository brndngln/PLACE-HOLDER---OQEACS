"""
System 42 — Drift, A/B Testing & Benchmark endpoints.

GET  /api/v1/drift-report       — drift report for an agent
POST /api/v1/ab-test            — start an A/B prompt test
GET  /api/v1/ab-test/{test_id}  — retrieve A/B test result
POST /api/v1/benchmark          — run full benchmark
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from src.config import settings
from src.models import (
    ABTestRequest,
    ABTestResult,
    BenchmarkResult,
    DriftReport,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["drift", "ab-test", "benchmark"])

# In-memory store for A/B test results (production would use DB)
_ab_results: dict[str, ABTestResult] = {}


# ── Drift ───────────────────────────────────────────────────────────


@router.get(
    "/drift-report",
    summary="Drift report for an agent",
    response_model=DriftReport,
)
async def get_drift_report(
    request: Request,
    agent_id: str = Query(default="gpt-4o", description="Agent to check"),
    days: int = Query(default=30, ge=1, le=365),
) -> DriftReport:
    """Generate a drift report for the given agent over the specified
    number of days."""
    monitor = request.app.state.monitor
    report = await monitor.drift_detector.detect_drift(agent_id, days=days)
    return report


# ── A/B Testing ─────────────────────────────────────────────────────


async def _score_prompt(prompt: str, test_cases: list[str], model_id: str) -> float:
    """Send each test case through the LiteLLM proxy using *prompt* as
    the system message and return a normalised score (0..1)."""
    scores: list[float] = []

    for case in test_cases:
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": case},
            ],
            "temperature": 0.0,
            "max_tokens": 2048,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{settings.LITELLM_URL}/v1/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                # Simple quality heuristic: length + code-block presence
                has_code = 1.0 if "def " in content or "class " in content else 0.0
                length_score = min(len(content) / 2000.0, 1.0)
                scores.append(round((has_code * 0.6 + length_score * 0.4), 4))
        except Exception as exc:
            logger.error("ab_test_prompt_error", error=str(exc))
            scores.append(0.0)

    return round(sum(scores) / len(scores), 4) if scores else 0.0


@router.post(
    "/ab-test",
    summary="Start A/B prompt test",
    response_model=ABTestResult,
)
async def create_ab_test(body: ABTestRequest) -> ABTestResult:
    """Run both prompts against the test cases and determine the
    winner."""
    test_id = str(uuid.uuid4())
    logger.info("ab_test_start", test_id=test_id, model=body.model_id)

    score_a = await _score_prompt(body.prompt_a, body.test_cases, body.model_id)
    score_b = await _score_prompt(body.prompt_b, body.test_cases, body.model_id)

    if score_a > score_b:
        winner = "a"
    elif score_b > score_a:
        winner = "b"
    else:
        winner = "tie"

    result = ABTestResult(
        id=test_id,
        prompt_a_score=score_a,
        prompt_b_score=score_b,
        winner=winner,
        details={
            "model_id": body.model_id,
            "test_case_count": len(body.test_cases),
            "prompt_a_preview": body.prompt_a[:100],
            "prompt_b_preview": body.prompt_b[:100],
        },
    )
    _ab_results[test_id] = result

    logger.info(
        "ab_test_complete",
        test_id=test_id,
        winner=winner,
        score_a=score_a,
        score_b=score_b,
    )
    return result


@router.get(
    "/ab-test/{test_id}",
    summary="Retrieve A/B test result",
    response_model=ABTestResult,
)
async def get_ab_test(test_id: str) -> ABTestResult:
    """Return the result of a previously executed A/B test."""
    result = _ab_results.get(test_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"A/B test {test_id} not found")
    return result


# ── Benchmark ───────────────────────────────────────────────────────


@router.post(
    "/benchmark",
    summary="Run full agent benchmark",
    response_model=BenchmarkResult,
)
async def run_benchmark(
    request: Request,
    agent_id: str = Query(default="gpt-4o", description="Agent to benchmark"),
) -> BenchmarkResult:
    """Execute all health sub-systems and return a consolidated
    benchmark score."""
    monitor = request.app.state.monitor
    logger.info("benchmark_requested", agent_id=agent_id)
    result = await monitor.run_full_benchmark(agent_id)
    return result
