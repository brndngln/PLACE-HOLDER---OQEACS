"""APScheduler-based job scheduler for periodic feed scans.

System 45 - Knowledge Freshness Service.
"""

import asyncio
from typing import Any, Optional

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config import settings

logger = structlog.get_logger(__name__)


class FreshnessScheduler:
    """Manages scheduled jobs for the Knowledge Freshness Service.

    Jobs:
        - scan_all_feeds: runs every SCAN_INTERVAL_HOURS (default 6h)
        - scan_security_advisories: runs every SECURITY_SCAN_INTERVAL_HOURS (default 1h)
        - generate_weekly_report: runs every Monday at 09:00 UTC
    """

    def __init__(self) -> None:
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._freshness_service: Any = None

    def configure(self, freshness_service: Any) -> None:
        """Bind the scheduler to a FreshnessService instance.

        Args:
            freshness_service: The FreshnessService to invoke on each job.
        """
        self._freshness_service = freshness_service

    async def _run_full_scan(self) -> None:
        """Execute the full feed scan job."""
        if self._freshness_service is None:
            logger.error("scheduler_no_freshness_service")
            return
        try:
            logger.info("scheduled_full_scan_start")
            report = await self._freshness_service.scan_all_feeds()
            logger.info(
                "scheduled_full_scan_complete",
                total=report.total_updates,
                relevant=report.relevant_updates,
            )
        except Exception as exc:
            logger.error("scheduled_full_scan_error", error=str(exc))

    async def _run_security_scan(self) -> None:
        """Execute the security advisory scan job."""
        if self._freshness_service is None:
            logger.error("scheduler_no_freshness_service")
            return
        try:
            logger.info("scheduled_security_scan_start")
            report = await self._freshness_service.scan_security_advisories()
            logger.info(
                "scheduled_security_scan_complete",
                total=report.total_updates,
                critical=len(report.breaking_changes),
            )
        except Exception as exc:
            logger.error("scheduled_security_scan_error", error=str(exc))

    async def _run_weekly_report(self) -> None:
        """Execute the weekly report generation job."""
        if self._freshness_service is None:
            logger.error("scheduler_no_freshness_service")
            return
        try:
            logger.info("scheduled_weekly_report_start")
            report = await self._freshness_service.generate_weekly_report()
            logger.info(
                "scheduled_weekly_report_complete",
                freshness_score=report.freshness_score,
            )
        except Exception as exc:
            logger.error("scheduled_weekly_report_error", error=str(exc))

    def start(self) -> None:
        """Start the scheduler with all configured jobs."""
        self._scheduler = AsyncIOScheduler(timezone="UTC")

        # Full scan every N hours
        self._scheduler.add_job(
            self._run_full_scan,
            trigger=IntervalTrigger(hours=settings.SCAN_INTERVAL_HOURS),
            id="full_scan",
            name="Full Feed Scan",
            replace_existing=True,
            max_instances=1,
        )

        # Security scan every N hours
        self._scheduler.add_job(
            self._run_security_scan,
            trigger=IntervalTrigger(hours=settings.SECURITY_SCAN_INTERVAL_HOURS),
            id="security_scan",
            name="Security Advisory Scan",
            replace_existing=True,
            max_instances=1,
        )

        # Weekly report every Monday at 09:00 UTC
        self._scheduler.add_job(
            self._run_weekly_report,
            trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
            id="weekly_report",
            name="Weekly Knowledge Report",
            replace_existing=True,
            max_instances=1,
        )

        self._scheduler.start()
        logger.info(
            "scheduler_started",
            scan_interval_hours=settings.SCAN_INTERVAL_HOURS,
            security_interval_hours=settings.SECURITY_SCAN_INTERVAL_HOURS,
            jobs=len(self._scheduler.get_jobs()),
        )

    def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            logger.info("scheduler_stopped")

    def get_jobs(self) -> list[dict[str, str]]:
        """Return information about all registered jobs.

        Returns:
            List of dicts with job id, name, and next_run_time.
        """
        if self._scheduler is None:
            return []
        return [
            {
                "id": job.id,
                "name": job.name or "",
                "next_run_time": str(job.next_run_time) if job.next_run_time else "paused",
            }
            for job in self._scheduler.get_jobs()
        ]
