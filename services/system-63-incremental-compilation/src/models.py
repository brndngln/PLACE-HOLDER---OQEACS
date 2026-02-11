from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BuildCache(BaseModel):
    id: str
    file_hash: str
    artifact_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    hit_count: int = 0


class IncrementalBuildRequest(BaseModel):
    changed_files: list[str]
    project_path: str


class BuildPlan(BaseModel):
    files_to_rebuild: list[str]
    files_cached: list[str]
    estimated_time_saved: float
    cache_hit_ratio: float


class DependencyGraph(BaseModel):
    nodes: list[str]
    edges: list[tuple[str, str]]
