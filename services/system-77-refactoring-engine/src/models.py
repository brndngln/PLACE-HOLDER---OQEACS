from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RefactoringOpportunity(BaseModel):
    id: str
    file_path: str
    type: Literal["dead_code", "duplication", "extract_method", "simplify_conditional", "extract_class", "inline_temp", "rename"]
    description: str
    risk: str
    estimated_effort: str


class RefactoringResult(BaseModel):
    opportunity_id: str
    success: bool
    original_code: str
    refactored_code: str
    tests_passing: bool
    diff: str


class TechDebtReport(BaseModel):
    total_items: int
    by_type: dict[str, int]
    top_priority: list[str]
    estimated_total_hours: float


class RefactoringPlan(BaseModel):
    opportunities: list[RefactoringOpportunity] = Field(default_factory=list)
    total_tech_debt_hours: float
    priority_order: list[str]
