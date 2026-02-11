from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from src.services.agent_assigner import AgentAssigner
from src.services.prd_parser import PRDParser
from src.services.task_decomposer import TaskDecomposer

router = APIRouter(prefix="/api/v1", tags=["projects"])
_projects: dict[str, dict] = {}


@router.post("/project")
def create_project(payload: dict):
    prd = PRDParser().parse(payload["prd_text"])
    epics = TaskDecomposer().decompose(prd)
    for epic in epics:
        AgentAssigner().assign(epic.stories)
    pid = f"PRJ-{uuid.uuid4().hex[:6]}"
    _projects[pid] = {"id": pid, "prd": prd, "epics": epics}
    return _projects[pid]


@router.get("/project/{project_id}")
def get_project(project_id: str):
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return _projects[project_id]
