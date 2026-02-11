"""
System 42 — Poison Pill endpoints.

POST /api/v1/poison-pill/run       — trigger a poison-pill run
GET  /api/v1/poison-pill/results   — retrieve stored results
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Query, Request

from src.models import PoisonPillReport, PoisonPillResult

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/poison-pill", tags=["poison-pills"])


@router.post(
    "/run",
    summary="Run poison-pill suite",
    response_model=PoisonPillReport,
)
async def run_poison_pills(
    request: Request,
    agent_id: str = Query(default="gpt-4o", description="Agent to test"),
) -> PoisonPillReport:
    """Execute the full poison-pill suite against the specified agent
    and return the report."""
    monitor = request.app.state.monitor
    logger.info("poison_pill_run_requested", agent_id=agent_id)
    report = await monitor.poison_runner.run_suite(agent_id)
    return report


@router.get(
    "/results",
    summary="Retrieve poison-pill results",
    response_model=list[PoisonPillResult],
)
async def get_poison_pill_results(
    request: Request,
    agent_id: str | None = Query(default=None, description="Filter by agent"),
) -> list[PoisonPillResult]:
    """Return all stored poison-pill results, optionally filtered by
    agent."""
    monitor = request.app.state.monitor
    results = monitor.poison_runner.get_results(agent_id)
    return results
