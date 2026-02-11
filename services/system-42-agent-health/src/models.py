"""
System 42 — Pydantic v2 data models.

Every model uses ``model_config = ConfigDict(from_attributes=True)`` so
ORM rows or plain dicts can be loaded with ``Model.model_validate()``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Poison Pill models ──────────────────────────────────────────────


class PoisonPillResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pill_id: str = Field(..., description="Unique identifier for the poison pill test")
    agent_id: str = Field(..., description="Agent under test")
    passed: bool = Field(..., description="True when the agent resisted the exploit")
    severity: str = Field(..., description="critical | high | medium | low")
    generated_code_hash: str = Field(
        default="", description="SHA-256 of generated code for audit trail"
    )
    timestamp: datetime = Field(default_factory=_utcnow)


class PoisonPillReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    total: int = Field(default=0, ge=0)
    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    critical_failures: list[str] = Field(
        default_factory=list,
        description="IDs of pills that failed at critical severity",
    )
    results: list[PoisonPillResult] = Field(default_factory=list)


# ── Golden Test models ──────────────────────────────────────────────


class GoldenTestResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    test_id: str = Field(..., description="Identifier for the golden test case")
    agent_id: str
    passed: bool
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utcnow)


# ── Drift Detection models ─────────────────────────────────────────


class DriftReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Historical performance snapshots (date, score, ...)",
    )
    drift_percentage: float = Field(
        default=0.0,
        description="Negative = degradation, positive = improvement",
    )


# ── Aggregate health model ─────────────────────────────────────────


class AgentHealthSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    poison_pill_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    golden_test_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    drift_status: str = Field(
        default="stable",
        description="stable | improving | degrading | unknown",
    )
    last_check: datetime = Field(default_factory=_utcnow)


# ── A/B Testing models ─────────────────────────────────────────────


class ABTestRequest(BaseModel):
    prompt_a: str = Field(..., min_length=1)
    prompt_b: str = Field(..., min_length=1)
    test_cases: list[str] = Field(..., min_length=1)
    model_id: str = Field(default="gpt-4o")


class ABTestResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    prompt_a_score: float = Field(default=0.0, ge=0.0, le=1.0)
    prompt_b_score: float = Field(default=0.0, ge=0.0, le=1.0)
    winner: str = Field(default="tie", description="a | b | tie")
    details: dict[str, Any] = Field(default_factory=dict)


# ── Benchmark models ───────────────────────────────────────────────


class BenchmarkResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="Category -> score mapping (e.g. security: 0.95)",
    )
    overall: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=_utcnow)
