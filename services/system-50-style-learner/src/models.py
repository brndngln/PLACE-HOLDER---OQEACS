from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StyleRule(BaseModel):
    name: str
    pattern: str
    description: str
    severity: Literal["low", "medium", "high"] = "medium"
    auto_fix: bool = False


class StyleProfile(BaseModel):
    id: str
    repo_name: str
    naming_convention: str
    import_style: str
    error_pattern: str
    logging_pattern: str
    test_style: str
    docstring_style: str
    type_hint_usage: str
    indent_style: str
    max_line_length: int = 120
    rules: list[StyleRule] = Field(default_factory=list)


class StyleViolation(BaseModel):
    rule: str
    line: int
    message: str
    severity: str


class StyleCheckRequest(BaseModel):
    code: str
    language: str = "python"
    profile_id: str


class StyleCheckResult(BaseModel):
    violations: list[StyleViolation] = Field(default_factory=list)
    score: float
    corrected_code: str


class LearnRequest(BaseModel):
    repo_path: str
    languages: list[str] = Field(default_factory=lambda: ["python"])
