"""
System 43 — APScheduler jobs.

Schedules:
    - Every 5 minutes — health check sweep across all services.
    - Hourly — full integration test suite.
    - Daily 06:00 UTC — comprehensive platform health report.
"""

from __future__ import annotations

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.services.test_runner import TestRunner
from src.utils.notifications import send_mattermost_alert

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


# -- Job functions ------------------------------------------------------------


async def _run_health_checks(runner: TestRunner) -> None:
    """Execute health checks against all registered services."""
    logger.info("scheduled_health_check_start")
    try:
        suite = await runner.run_health_checks()
        logger.info(
            "scheduled_health_check_done",
            total=suite.total,
            passed=suite.passed,
            failed=suite.failed,
            duration_ms=suite.duration_ms,
        )
        # Alert on failures
        if suite.failed > 0:
            failed_services = [
                r.test_case_id for r in suite.results if not r.passed
            ]
            await send_mattermost_alert(
                title="Health Check Failures Detected",
                message=(
                    f"{suite.failed}/{suite.total} services failed health checks."
                ),
                severity="high" if suite.failed <= 3 else "critical",
                fields={
                    "Passed": str(suite.passed),
                    "Failed": str(suite.failed),
                    "Duration": f"{suite.duration_ms:.0f}ms",
                    "Failed Services": ", ".join(failed_services[:10]),
                },
            )
    except Exception as exc:
        logger.error("scheduled_health_check_error", error=str(exc))


async def _run_integration_suite(runner: TestRunner) -> None:
    """Execute the full integration test suite."""
    logger.info("scheduled_integration_suite_start")
    try:
        suite = await runner.run_integration_suite()
        logger.info(
            "scheduled_integration_suite_done",
            total=suite.total,
            passed=suite.passed,
            failed=suite.failed,
            duration_ms=suite.duration_ms,
        )
        if suite.failed > 0:
            await send_mattermost_alert(
                title="Integration Test Failures",
                message=(
                    f"{suite.failed}/{suite.total} integration tests failed."
                ),
                severity="high",
                fields={
                    "Passed": str(suite.passed),
                    "Failed": str(suite.failed),
                    "Duration": f"{suite.duration_ms:.0f}ms",
                },
            )
    except Exception as exc:
        logger.error("scheduled_integration_suite_error", error=str(exc))


async def _run_daily_report(runner: TestRunner) -> None:
    """Generate and broadcast the daily comprehensive platform report."""
    logger.info("scheduled_daily_report_start")
    try:
        report = await runner.run_full_suite()
        logger.info(
            "scheduled_daily_report_done",
            score=report.score,
            healthy=report.services_healthy,
            degraded=report.services_degraded,
            down=report.services_down,
        )
        severity = "success"
        if report.services_degraded > 0:
            severity = "medium"
        if report.services_down > 0:
            severity = "critical"

        await send_mattermost_alert(
            title="Daily Platform Health Report",
            message=(
                f"Platform score: **{report.score:.1f}/100**\n\n"
                f"Tested {report.services_tested} services."
            ),
            severity=severity,
            fields={
                "Healthy": str(report.services_healthy),
                "Degraded": str(report.services_degraded),
                "Down": str(report.services_down),
                "Score": f"{report.score:.1f}",
            },
        )
    except Exception as exc:
        logger.error("scheduled_daily_report_error", error=str(exc))


# -- Lifecycle helpers --------------------------------------------------------


def init_scheduler(runner: TestRunner) -> AsyncIOScheduler:
    """Create, configure, and return (but do not start) the scheduler."""
    global _scheduler  # noqa: PLW0603

    scheduler = AsyncIOScheduler(timezone="UTC")

    # Every 5 minutes — health checks
    scheduler.add_job(
        _run_health_checks,
        trigger=IntervalTrigger(minutes=5),
        args=[runner],
        id="health_checks_5min",
        name="Health checks every 5 minutes",
        replace_existing=True,
        max_instances=1,
    )

    # Hourly — integration suite
    scheduler.add_job(
        _run_integration_suite,
        trigger=IntervalTrigger(hours=1),
        args=[runner],
        id="integration_suite_hourly",
        name="Hourly integration test suite",
        replace_existing=True,
        max_instances=1,
    )

    # Daily at 06:00 UTC — comprehensive report
    scheduler.add_job(
        _run_daily_report,
        trigger=CronTrigger(hour=6, minute=0),
        args=[runner],
        id="daily_platform_report",
        name="Daily comprehensive platform report",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler = scheduler
    logger.info("scheduler_initialized", jobs=len(scheduler.get_jobs()))
    return scheduler


def get_scheduler() -> AsyncIOScheduler | None:
    """Return the active scheduler instance (if any)."""
    return _scheduler
