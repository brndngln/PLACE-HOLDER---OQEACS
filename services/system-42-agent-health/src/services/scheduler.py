"""
System 42 — APScheduler jobs.

Schedules:
    - Daily  03:00 UTC  — poison-pill sweep across all registered agents.
    - Weekly Sunday 04:00 UTC — full golden-test run.
    - Hourly — drift detection on all agents.
"""

from __future__ import annotations

from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.services.health_monitor import AgentHealthMonitor

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


# ── Job functions ───────────────────────────────────────────────────

async def _run_poison_pills(monitor: AgentHealthMonitor) -> None:
    """Iterate over all known agents and run the poison-pill suite."""
    agents = await monitor.list_agents()
    logger.info("scheduled_poison_pill_start", agent_count=len(agents))
    for agent_id in agents:
        try:
            report = await monitor.poison_runner.run_suite(agent_id)
            logger.info(
                "scheduled_poison_pill_done",
                agent_id=agent_id,
                passed=report.passed,
                failed=report.failed,
            )
        except Exception as exc:
            logger.error(
                "scheduled_poison_pill_error",
                agent_id=agent_id,
                error=str(exc),
            )


async def _run_golden_tests(monitor: AgentHealthMonitor) -> None:
    """Iterate over all known agents and run golden tests."""
    agents = await monitor.list_agents()
    logger.info("scheduled_golden_test_start", agent_count=len(agents))
    for agent_id in agents:
        try:
            results = await monitor.golden_runner.run_suite(agent_id)
            passed = sum(1 for r in results if r.passed)
            logger.info(
                "scheduled_golden_test_done",
                agent_id=agent_id,
                passed=passed,
                total=len(results),
            )
        except Exception as exc:
            logger.error(
                "scheduled_golden_test_error",
                agent_id=agent_id,
                error=str(exc),
            )


async def _run_drift_checks(monitor: AgentHealthMonitor) -> None:
    """Iterate over all known agents and check for drift."""
    agents = await monitor.list_agents()
    logger.info("scheduled_drift_check_start", agent_count=len(agents))
    for agent_id in agents:
        try:
            report = await monitor.drift_detector.detect_drift(agent_id)
            logger.info(
                "scheduled_drift_check_done",
                agent_id=agent_id,
                drift_pct=report.drift_percentage,
            )
        except Exception as exc:
            logger.error(
                "scheduled_drift_check_error",
                agent_id=agent_id,
                error=str(exc),
            )


# ── Lifecycle helpers ───────────────────────────────────────────────

def init_scheduler(monitor: AgentHealthMonitor) -> AsyncIOScheduler:
    """Create, configure, and return (but do not start) the scheduler."""
    global _scheduler  # noqa: PLW0603

    scheduler = AsyncIOScheduler(timezone="UTC")

    # Daily at 03:00 UTC — poison pills
    scheduler.add_job(
        _run_poison_pills,
        trigger=CronTrigger(hour=3, minute=0),
        args=[monitor],
        id="daily_poison_pills",
        name="Daily poison-pill sweep",
        replace_existing=True,
        max_instances=1,
    )

    # Weekly Sunday at 04:00 UTC — golden tests
    scheduler.add_job(
        _run_golden_tests,
        trigger=CronTrigger(day_of_week="sun", hour=4, minute=0),
        args=[monitor],
        id="weekly_golden_tests",
        name="Weekly golden-test run",
        replace_existing=True,
        max_instances=1,
    )

    # Hourly — drift checks
    scheduler.add_job(
        _run_drift_checks,
        trigger=IntervalTrigger(hours=1),
        args=[monitor],
        id="hourly_drift_checks",
        name="Hourly drift detection",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler = scheduler
    logger.info("scheduler_initialized", jobs=len(scheduler.get_jobs()))
    return scheduler


def get_scheduler() -> AsyncIOScheduler | None:
    """Return the active scheduler instance (if any)."""
    return _scheduler
