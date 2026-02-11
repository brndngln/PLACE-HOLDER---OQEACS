from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Mutant(BaseModel):
    id: str
    operator: str
    line: int
    original: str
    mutated: str
    killed: bool
    killing_test: str | None = None


class MutationResult(BaseModel):
    original_code: str
    mutants_generated: int
    mutants_killed: int
    mutants_survived: int
    mutation_score: float
    surviving_mutants: list[Mutant] = Field(default_factory=list)


class TestImpactResult(BaseModel):
    changed_files: list[str]
    affected_tests: list[str]
    priority_order: list[str]
    estimated_time: float


class CoverageGap(BaseModel):
    file: str
    function: str
    uncovered_lines: list[int]
    risk_level: str


class TestQualityScore(BaseModel):
    file: str
    total_tests: int
    effective_tests: int
    quality_score: float
    issues: list[str] = Field(default_factory=list)


class FlakyTestReport(BaseModel):
    test_name: str
    file: str
    failure_rate: float
    last_flake: str
    root_cause_guess: str


class GenerateTestsRequest(BaseModel):
    code: str
    language: str
    framework: str = "pytest"


class GenerateTestsResult(BaseModel):
    tests_code: str
    test_count: int
    coverage_estimate: float
