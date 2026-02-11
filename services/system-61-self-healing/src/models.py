from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorEvent(BaseModel):
    service: str
    error_type: str
    message: str
    traceback: str = ""
    timestamp: str
    frequency: int = 1


class HealingAttempt(BaseModel):
    id: str
    error_event: ErrorEvent
    generated_fix: str
    verification_status: str
    pr_url: str | None = None
    attempts: int = 1


class HealingResult(BaseModel):
    success: bool
    fix_code: str
    diff: str
    tests_passed: bool
    pr_created: bool


class HealingConfig(BaseModel):
    auto_pr: bool = True
    max_attempts: int = 3
    confidence_threshold: float = 0.7


class PipelineStatus(BaseModel):
    active_healings: int
    total_healed: int
    total_failed: int
    success_rate: float
