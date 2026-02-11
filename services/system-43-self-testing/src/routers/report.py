"""
System 43 — Platform report and service-listing routes.

GET /api/v1/report    — latest platform health report
GET /api/v1/services  — list all monitored services with status
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

from src.models import PlatformHealthReport, ServiceInfo

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["report"])

_runner_ref: Any = None


def set_runner(runner: Any) -> None:
    """Called at startup to wire the TestRunner into this module."""
    global _runner_ref  # noqa: PLW0603
    _runner_ref = runner


def _get_runner() -> Any:
    if _runner_ref is None:
        raise HTTPException(status_code=503, detail="TestRunner not initialized")
    return _runner_ref


@router.get("/report", response_model=PlatformHealthReport)
async def get_platform_report() -> PlatformHealthReport:
    """Return the latest platform health report.

    If no report has been generated yet, triggers a fresh full suite run
    on-demand so the caller always receives data.
    """
    runner = _get_runner()
    report = runner.latest_report
    if report is None:
        logger.info("report_not_cached_running_now")
        report = await runner.run_full_suite()
    return report


@router.get("/services", response_model=list[ServiceInfo])
async def list_services() -> list[ServiceInfo]:
    """Return every monitored service with its last-known health status."""
    runner = _get_runner()
    return runner.list_services()
