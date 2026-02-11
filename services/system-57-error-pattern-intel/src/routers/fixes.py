from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.models import FixTemplate
from src.routers.errors import _fixes

router = APIRouter(prefix="/api/v1", tags=["fixes"])


@router.get("/fixes/{pattern_id}")
def get_fix(pattern_id: str):
    fix = _fixes.get_fix(pattern_id)
    if not fix:
        raise HTTPException(status_code=404, detail="Fix not found")
    return fix


@router.post("/fixes")
def add_fix(fix: FixTemplate):
    _fixes.store_fix(fix.pattern_id, fix)
    return fix


@router.get("/fixes/stats")
def stats():
    return _fixes.stats()
