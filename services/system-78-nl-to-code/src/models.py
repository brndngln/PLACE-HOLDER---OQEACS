from __future__ import annotations

from pydantic import BaseModel, Field


class NLRequest(BaseModel):
    description: str
    tech_stack: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class ProjectBlueprint(BaseModel):
    name: str
    structure: dict
    services: list[str]
    database_schema: str
    api_endpoints: list[str]
    estimated_files: int


class GeneratedProject(BaseModel):
    blueprint: ProjectBlueprint
    files: dict[str, str]
    total_files: int
    total_lines: int
    readme: str
    docker_compose: str


class RefinementRequest(BaseModel):
    project_id: str
    instruction: str
