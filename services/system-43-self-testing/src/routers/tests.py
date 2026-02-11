"""
System 43 — Test execution API routes.

POST /api/v1/run              — trigger full test suite
GET  /api/v1/results          — latest results
GET  /api/v1/results/{id}     — specific suite result by ID
POST /api/v1/run/health       — health checks only
POST /api/v1/run/integration  — integration suite only
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

from src.models import RunSuiteRequest, TestSuiteResult

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["tests"])

# The TestRunner instance is injected at startup via app.state.
# We access it through the request's app reference within each endpoint.

_runner_ref: Any = None


def set_runner(runner: Any) -> None:
    """Called at startup to wire the TestRunner into this module."""
    global _runner_ref  # noqa: PLW0603
    _runner_ref = runner


def _get_runner() -> Any:
    if _runner_ref is None:
        raise HTTPException(status_code=503, detail="TestRunner not initialized")
    return _runner_ref


# -- result history (in-memory ring buffer) -----------------------------------

_result_store: dict[str, TestSuiteResult] = {}
_MAX_RESULTS = 200


def _store_result(suite: TestSuiteResult) -> None:
    _result_store[suite.id] = suite
    # Evict oldest if over limit
    if len(_result_store) > _MAX_RESULTS:
        oldest_key = next(iter(_result_store))
        _result_store.pop(oldest_key, None)


# -- endpoints ----------------------------------------------------------------


@router.post("/run", response_model=TestSuiteResult)
async def run_full_suite(body: RunSuiteRequest | None = None) -> TestSuiteResult:
    """Trigger a full test suite (health checks + integration tests).

    Returns the combined ``TestSuiteResult`` immediately upon completion.
    """
    runner = _get_runner()
    logger.info("api_run_full_suite", services=body.services if body else None)

    report = await runner.run_full_suite(request=body)

    # Store both sub-suites
    for suite in report.suite_results:
        _store_result(suite)

    # Return the health-check suite as the primary result;
    # the full report is available via /api/v1/report
    combined = TestSuiteResult(
        suite_name=body.suite_name if body else "full-suite",
        total=sum(s.total for s in report.suite_results),
        passed=sum(s.passed for s in report.suite_results),
        failed=sum(s.failed for s in report.suite_results),
        errors=sum(s.errors for s in report.suite_results),
        results=[r for s in report.suite_results for r in s.results],
        started_at=report.suite_results[0].started_at if report.suite_results else report.timestamp,
        completed_at=report.suite_results[-1].completed_at if report.suite_results else None,
        duration_ms=sum(s.duration_ms for s in report.suite_results),
    )
    _store_result(combined)
    return combined


@router.get("/results", response_model=list[TestSuiteResult])
async def list_results(limit: int = 20) -> list[TestSuiteResult]:
    """Return the latest test suite results, most recent first."""
    items = list(_result_store.values())
    items.sort(key=lambda s: s.started_at, reverse=True)
    return items[:limit]


@router.get("/results/{result_id}", response_model=TestSuiteResult)
async def get_result(result_id: str) -> TestSuiteResult:
    """Retrieve a specific suite result by its ID."""
    suite = _result_store.get(result_id)
    if suite is None:
        raise HTTPException(status_code=404, detail=f"Result {result_id} not found")
    return suite


@router.post("/run/health", response_model=TestSuiteResult)
async def run_health_only(
    services: list[str] | None = None,
) -> TestSuiteResult:
    """Trigger health checks only (no integration tests).

    Optionally restrict to specific services via the query body.
    """
    runner = _get_runner()
    logger.info("api_run_health_only", services=services)
    suite = await runner.run_health_checks(services=services)
    _store_result(suite)
    return suite


@router.post("/run/integration", response_model=TestSuiteResult)
async def run_integration_only(
    services: list[str] | None = None,
) -> TestSuiteResult:
    """Trigger the integration test suite only (no health checks).

    Optionally restrict to specific services via the query body.
    """
    runner = _get_runner()
    logger.info("api_run_integration_only", services=services)
    suite = await runner.run_integration_suite(services=services)
    _store_result(suite)
    return suite
