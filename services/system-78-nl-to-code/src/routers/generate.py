from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from src.models import NLRequest, RefinementRequest
from src.services.blueprint_generator import BlueprintGenerator
from src.services.code_orchestrator import CodeOrchestrator
from src.services.refinement_engine import RefinementEngine

router = APIRouter(prefix="/api/v1", tags=["nl-code"])
_projects: dict[str, dict] = {}


@router.post("/generate")
def generate(req: NLRequest):
    blueprint = BlueprintGenerator().generate(req)
    project = CodeOrchestrator().generate_project(blueprint)
    pid = f"NL-{uuid.uuid4().hex[:8]}"
    _projects[pid] = project
    return {"project_id": pid, **project.model_dump()}


@router.get("/project/{project_id}")
def project(project_id: str):
    item = _projects.get(project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    return item


@router.post("/refine")
def refine(req: RefinementRequest):
    item = _projects.get(req.project_id)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    refined = RefinementEngine().refine(item, req.instruction)
    _projects[req.project_id] = refined
    return refined
