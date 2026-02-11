from __future__ import annotations

import uuid

from fastapi import APIRouter

from src.models import SprintPlan
from src.routers.projects import _projects
from src.services.progress_tracker import ProgressTracker

router = APIRouter(prefix="/api/v1", tags=["sprints"])
_sprints: dict[str, SprintPlan] = {}


@router.post("/sprint/plan")
def plan(payload: dict):
    project = _projects[payload["project_id"]]
    stories = [s for e in project["epics"] for s in e.stories]
    sprint = SprintPlan(id=f"SP-{uuid.uuid4().hex[:6]}", stories=stories, total_points=len(stories) * 3, duration_days=payload.get("duration_days", 14))
    _sprints[sprint.id] = sprint
    return sprint


@router.get("/sprint/{sprint_id}/report")
def report(sprint_id: str):
    sprint = _sprints[sprint_id]
    return ProgressTracker().generate_report(sprint_id, sprint.stories)
