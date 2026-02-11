from __future__ import annotations

from pydantic import BaseModel, Field


class PRD(BaseModel):
    title: str
    description: str
    requirements: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class Story(BaseModel):
    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    estimated_complexity: str
    assigned_agent: str
    status: str


class Epic(BaseModel):
    id: str
    title: str
    stories: list[Story]
    estimated_points: int


class SprintPlan(BaseModel):
    id: str
    stories: list[Story]
    total_points: int
    duration_days: int


class ProgressReport(BaseModel):
    sprint_id: str
    completed: int
    in_progress: int
    blocked: int
    velocity: float
    burndown: list[dict]
