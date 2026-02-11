from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from src.models import IncrementalBuildRequest
from src.services.build_planner import BuildPlanner
from src.services.cache_manager import CacheManager
from src.services.dependency_tracker import DependencyTracker

router = APIRouter(prefix="/api/v1", tags=["build"])
_cache = CacheManager()


@router.post("/plan")
def plan(req: IncrementalBuildRequest):
    graph = DependencyTracker().build_dep_graph(req.project_path)
    return BuildPlanner().plan_build(req.changed_files, graph)


@router.post("/cache/invalidate")
def invalidate(payload: dict):
    return {"invalidated": _cache.invalidate(payload.get("file_hash", ""))}


@router.get("/cache/stats")
def stats():
    return _cache.get_cache_stats()
