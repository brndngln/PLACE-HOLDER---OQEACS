from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PromptVersion(BaseModel):
    id: str
    name: str
    system_prompt: str
    template: str
    version: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    performance_score: float = 0.0
    token_count: int = 0


class ABTestConfig(BaseModel):
    prompt_a_id: str
    prompt_b_id: str
    task_type: str
    sample_size: int
    metric: str


class ABTestResult(BaseModel):
    config: ABTestConfig
    prompt_a_score: float
    prompt_b_score: float
    winner: str
    confidence_interval: tuple[float, float]
    p_value: float


class PromptOptimizeRequest(BaseModel):
    current_prompt: str
    task_description: str
    optimization_goal: Literal["quality", "cost", "speed", "all"]


class OptimizedPrompt(BaseModel):
    original: str
    optimized: str
    token_reduction_pct: float
    quality_estimate: float


class DecayReport(BaseModel):
    prompt_id: str
    current_score: float
    baseline_score: float
    decay_pct: float
    recommendation: str
