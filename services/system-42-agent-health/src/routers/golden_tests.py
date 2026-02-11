"""
System 42 — Golden Test endpoints.

POST /api/v1/golden-tests/run      — trigger a golden-test run
GET  /api/v1/golden-tests/results  — retrieve stored results
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Query, Request

from src.models import GoldenTestResult

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/golden-tests", tags=["golden-tests"])


@router.post(
    "/run",
    summary="Run golden-test suite",
    response_model=list[GoldenTestResult],
)
async def run_golden_tests(
    request: Request,
    agent_id: str = Query(default="gpt-4o", description="Agent to test"),
) -> list[GoldenTestResult]:
    """Execute all golden tests against the specified agent."""
    monitor = request.app.state.monitor
    logger.info("golden_test_run_requested", agent_id=agent_id)
    results = await monitor.golden_runner.run_suite(agent_id)
    return results


@router.get(
    "/results",
    summary="Retrieve golden-test results",
    response_model=list[GoldenTestResult],
)
async def get_golden_test_results(
    request: Request,
    agent_id: str | None = Query(default=None, description="Filter by agent"),
) -> list[GoldenTestResult]:
    """Return all stored golden-test results, optionally filtered by
    agent."""
    monitor = request.app.state.monitor
    results = monitor.golden_runner.get_results(agent_id)
    return results
