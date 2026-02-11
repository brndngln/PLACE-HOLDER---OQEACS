from __future__ import annotations

from fastapi import APIRouter

from src.models import DocGenerationRequest
from src.services.diagram_generator import DiagramGenerator
from src.services.doc_generator import DocGenerator
from src.services.sync_checker import SyncChecker

router = APIRouter(prefix="/api/v1", tags=["docs"])


@router.post("/generate")
def generate(req: DocGenerationRequest):
    return DocGenerator().generate(req)


@router.post("/sync-check")
def sync_check(payload: dict):
    return SyncChecker().check_sync(payload.get("code_path", ""), payload.get("doc_path", ""))


@router.post("/diagram")
def diagram(payload: dict):
    if "code_path" in payload:
        return DiagramGenerator().generate_architecture(payload["code_path"])
    return DiagramGenerator().generate_architecture_from_code(payload.get("code", ""))
