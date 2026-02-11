from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TrainingDataEntry(BaseModel):
    instruction: str
    input_text: str
    output_text: str
    quality_score: float
    source: str
    language: str
    task_type: str


class DatasetStats(BaseModel):
    total_entries: int
    by_language: dict[str, int]
    by_task_type: dict[str, int]
    avg_quality: float


class LoRAConfig(BaseModel):
    rank: int = 16
    alpha: int = 32
    dropout: float = 0.05
    target_modules: list[str] = Field(default_factory=lambda: ["q_proj", "v_proj"])


class FineTuneJob(BaseModel):
    id: str
    base_model: str
    dataset_id: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    eval_results: list[dict] = Field(default_factory=list)


class EvalResult(BaseModel):
    benchmark: str
    score: float
    baseline_score: float
    improvement_pct: float


class CollectRequest(BaseModel):
    source: str
    days_back: int = 7
