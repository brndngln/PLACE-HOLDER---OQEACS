from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FitnessRule(BaseModel):
    name: str
    description: str
    severity: Literal["low", "medium", "high"] = "medium"


class DependencyRule(BaseModel):
    source_pattern: str
    forbidden_pattern: str
    reason: str


class LayerDefinition(BaseModel):
    name: str
    allowed_dependencies: list[str] = Field(default_factory=list)


class Violation(BaseModel):
    rule: str
    file: str
    message: str
    severity: str


class CircularDependency(BaseModel):
    cycle: list[str]


class APIContractDrift(BaseModel):
    endpoint: str
    drift_type: str
    notes: str


class FitnessResult(BaseModel):
    score: float
    violations: list[Violation] = Field(default_factory=list)


class ArchitectureReport(BaseModel):
    result: FitnessResult
    circular_dependencies: list[CircularDependency] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    codebase_path: str
    rules: list[DependencyRule] = Field(default_factory=list)
    layers: list[LayerDefinition] = Field(default_factory=list)
