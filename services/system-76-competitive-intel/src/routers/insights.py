from __future__ import annotations

from fastapi import APIRouter

from src.services.insight_generator import InsightGenerator
from src.services.project_monitor import ProjectMonitor
from src.services.trend_tracker import TrendTracker

router = APIRouter(prefix="/api/v1", tags=["insights"])


@router.get("/insights/{topic}")
def insight(topic: str):
    return InsightGenerator().get_insights(topic)


@router.get("/trends/{domain}")
def trends(domain: str):
    return TrendTracker().detect_trends(domain)


@router.get("/projects")
def projects():
    return ProjectMonitor().list_projects()
