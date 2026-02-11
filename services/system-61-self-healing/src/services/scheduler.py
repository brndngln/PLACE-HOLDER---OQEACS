from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


def create_scheduler(run_pipeline, report_status):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_pipeline, trigger=IntervalTrigger(minutes=2), id="heal-pipeline", replace_existing=True)
    scheduler.add_job(report_status, trigger=IntervalTrigger(hours=1), id="heal-status", replace_existing=True)
    return scheduler
