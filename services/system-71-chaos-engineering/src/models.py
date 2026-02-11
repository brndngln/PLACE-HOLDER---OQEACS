from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChaosExperiment(BaseModel):
    id: str
    name: str
    target_service: str
    failure_type: Literal["latency", "error", "cpu", "memory", "network_partition", "disk_full", "dns_failure"]
    parameters: dict = Field(default_factory=dict)
    duration_seconds: int
    steady_state_hypothesis: str
    status: str = "planned"


class ExperimentResult(BaseModel):
    experiment_id: str
    started_at: datetime
    ended_at: datetime
    steady_state_before: bool
    steady_state_after: bool
    passed: bool
    observations: list[str]
    rollback_performed: bool


class GameDay(BaseModel):
    id: str
    name: str
    experiments: list[str]
    schedule: str
    participants: list[str]


class ResilienceReport(BaseModel):
    service: str
    experiments_run: int
    experiments_passed: int
    resilience_score: float
    weaknesses: list[str] = Field(default_factory=list)
