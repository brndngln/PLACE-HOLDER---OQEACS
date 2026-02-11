from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorPattern(BaseModel):
    id: str
    language: str
    error_type: str
    pattern_signature: str
    description: str
    root_causes: list[str] = Field(default_factory=list)
    frequency: int = 1
    fix_templates: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    pattern: ErrorPattern
    similarity: float
    suggested_fix: str


class ErrorReport(BaseModel):
    code: str
    language: str
    predicted_errors: list[str]
    risk_score: float
    suggested_fixes: list[str]


class FixTemplate(BaseModel):
    pattern_id: str
    fix_description: str
    code_before: str
    code_after: str
    confidence: float = 0.5


class IngestRequest(BaseModel):
    error_message: str
    traceback: str = ""
    code_context: str = ""
    language: str = "python"
    service_name: str = "unknown"


class PredictRequest(BaseModel):
    code: str
    language: str = "python"
