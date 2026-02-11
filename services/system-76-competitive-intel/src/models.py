from __future__ import annotations

from pydantic import BaseModel, Field


class ImplementationExample(BaseModel):
    project: str
    language: str
    approach: str
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    stars: int = 0
    source_url: str = ""


class CompetitiveInsight(BaseModel):
    topic: str
    implementations: list[ImplementationExample]
    best_practices: list[str]
    trends: list[str]


class TrendReport(BaseModel):
    topic: str
    current_state: str
    direction: str
    key_projects: list[str]
