from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    code: str
    language: str


class Issue(BaseModel):
    severity: str
    category: str
    line: int
    column: int = 1
    message: str
    suggestion: str
    rule_id: str


class AnalysisResult(BaseModel):
    language: str
    issues: list[Issue] = Field(default_factory=list)
    score: float
    summary: str


class LanguageSupport(BaseModel):
    languages: list[dict]
