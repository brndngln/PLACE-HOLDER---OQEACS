from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.services.version_manager import PromptVersionManager

router = APIRouter(prefix="/api/v1", tags=["prompts"])
_mgr = PromptVersionManager()


@router.post("/prompts")
def create(payload: dict):
    return _mgr.create_version(payload["name"], payload["system_prompt"], payload.get("template", ""))


@router.get("/prompts")
def list_prompts():
    return _mgr.list_versions()


@router.get("/prompts/{prompt_id}")
def get_prompt(prompt_id: str):
    item = _mgr.get_version(prompt_id)
    if not item:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return item
