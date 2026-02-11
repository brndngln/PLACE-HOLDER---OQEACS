"""System 41: Formal Verification Engine — Pydantic v2 data models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class VerificationTool(str, Enum):
    TLA_PLUS = "tla_plus"
    CBMC = "cbmc"
    DAFNY = "dafny"
    SPIN = "spin"
    ALLOY = "alloy"
    CROSSHAIR = "crosshair"
    KANI = "kani"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class VerificationRequest(BaseModel):
    source_code: str = Field(description="The code to verify")
    language: str = Field(description="Source language: python, c, cpp, rust, protocol, dafny")
    tool: VerificationTool | None = Field(
        default=None, description="Specific tool to use; auto-selected if None"
    )
    properties: list[str] = Field(
        default_factory=list,
        description="Properties to verify: memory_safety, deadlock_freedom, liveness, bounds_check, contracts",
    )
    timeout_seconds: int = Field(default=300, ge=10, le=3600)
    depth: int = Field(default=100, ge=1, le=10000, description="Unwind depth for bounded model checking")
    project_id: str | None = None


class SpecGenerationRequest(BaseModel):
    source_code: str
    language: str
    target_spec: VerificationTool = VerificationTool.CROSSHAIR
    description: str = ""


class VerificationResult(BaseModel):
    id: str
    status: VerificationStatus
    tool: VerificationTool
    language: str
    properties_checked: list[str]
    properties_passed: list[str]
    properties_failed: list[str]
    counterexamples: list[CounterExample] = []
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class CounterExample(BaseModel):
    property_name: str
    description: str
    trace: list[str] = []
    input_values: dict = {}


class SpecGenerationResult(BaseModel):
    id: str
    original_language: str
    target_spec: VerificationTool
    generated_spec: str
    annotations: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0)


class ToolInfo(BaseModel):
    name: str
    tool_id: VerificationTool
    purpose: str
    supported_languages: list[str]
    available: bool
    version: str = "unknown"


class ProofRecord(BaseModel):
    id: str
    project_id: str | None
    tool: VerificationTool
    status: VerificationStatus
    properties_count: int
    properties_passed: int
    execution_time_ms: int
    created_at: datetime
