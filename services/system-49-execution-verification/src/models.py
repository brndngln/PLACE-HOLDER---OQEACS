"""Pydantic v2 models for System 49: Execution Verification Loop."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class TestCase(BaseModel):
    """A single test case with expected input/output."""

    input: dict[str, Any] = Field(default_factory=dict, description="Input data for the test case")
    expected_output: Any = Field(description="Expected output value")
    description: str = Field(default="", description="Human-readable test description")


class ExecutionRequest(BaseModel):
    """Request to execute and verify a piece of code."""

    code: str = Field(description="Source code to execute")
    language: Literal["python", "javascript", "typescript", "go", "rust", "bash"] = Field(
        description="Programming language"
    )
    test_cases: list[TestCase] | None = Field(
        default=None, description="Test cases to validate; auto-generated if omitted"
    )
    dependencies: list[str] = Field(default_factory=list, description="Package dependencies to install")
    entry_point: str | None = Field(
        default=None, description="Function or script entry point (e.g. 'main')"
    )


class RegenerationRequest(BaseModel):
    """Request sent to LiteLLM to regenerate broken code."""

    code: str = Field(description="Code that failed execution")
    error: str = Field(description="Error output from the failed execution")
    language: str = Field(description="Programming language of the code")
    attempt: int = Field(description="Which regeneration attempt this is (1-based)")


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class TestCaseResult(BaseModel):
    """Result of running a single test case."""

    test_case: TestCase
    passed: bool = False
    actual_output: Any = None
    error: str | None = None


class ExecutionResult(BaseModel):
    """Result of a single code execution."""

    success: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    test_results: list[TestCaseResult] = Field(default_factory=list)


class VerificationResult(BaseModel):
    """Full result of the verification loop (possibly spanning multiple attempts)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_code: str = ""
    verified_code: str = ""
    language: str = "python"
    attempts: int = 0
    all_results: list[ExecutionResult] = Field(default_factory=list)
    final_status: Literal["verified", "failed", "timeout"] = "failed"
    fixes_applied: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# API response helpers
# ---------------------------------------------------------------------------


class TestGenerationRequest(BaseModel):
    """Request to auto-generate test cases for code."""

    code: str = Field(description="Source code to generate tests for")
    language: Literal["python", "javascript", "typescript", "go", "rust", "bash"] = Field(
        description="Programming language"
    )


class TestRunRequest(BaseModel):
    """Request to run test cases against code."""

    code: str = Field(description="Source code to test")
    language: Literal["python", "javascript", "typescript", "go", "rust", "bash"] = Field(
        description="Programming language"
    )
    test_cases: list[TestCase] = Field(description="Test cases to run")
