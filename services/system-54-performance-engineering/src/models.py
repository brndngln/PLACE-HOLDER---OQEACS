from __future__ import annotations

from pydantic import BaseModel, Field


class Issue(BaseModel):
    category: str
    severity: str
    line: int
    message: str
    suggestion: str


class FunctionComplexity(BaseModel):
    function_name: str
    line: int
    cyclomatic: int
    cognitive: int


class ComplexityReport(BaseModel):
    language: str
    functions: list[FunctionComplexity] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    score: float


class N1QueryDetection(BaseModel):
    line: int
    pattern: str
    suggestion: str


class MemoryLeakPattern(BaseModel):
    line: int
    pattern: str
    suggestion: str


class PerformanceRegression(BaseModel):
    metric: str
    baseline: float
    current: float
    regression_pct: float
    severity: str


class AnalyzeRequest(BaseModel):
    code: str
    language: str = "python"
