"""System 40: Context Compiler — Pydantic v2 data models."""
from datetime import datetime
from pydantic import BaseModel, Field


class ContextBlock(BaseModel):
    source: str
    content: str
    token_count: int
    relevance_score: float = Field(ge=0.0, le=1.0)
    metadata: dict = {}


class ContextRequest(BaseModel):
    task_id: str
    task_type: str = Field(description="generate, review, fix, test, refactor")
    agent_role: str = Field(description="architect, developer, tester, reviewer, optimizer, security")
    project_id: str
    task_description: str
    referenced_files: list[str] = []
    error_context: str | None = None
    token_budget: int = 128000
    model_id: str = "devstral-2"
    tags: list[str] = []


class ContextResponse(BaseModel):
    task_id: str
    compiled_context: str
    blocks_included: list[ContextBlock]
    blocks_excluded: list[ContextBlock]
    total_tokens: int
    budget_used_pct: float
    kv_cache_hint: dict


class EffectivenessReport(BaseModel):
    task_id: str
    context_hash: str
    output_quality_score: float = Field(ge=0.0, le=1.0)
    task_success: bool
    feedback: str | None = None


class ContextTemplate(BaseModel):
    id: str | None = None
    name: str
    task_type: str
    agent_role: str
    priority_overrides: dict = {}
    token_budget_override: int | None = None
    tags: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ContextStats(BaseModel):
    total_compilations: int
    avg_tokens_used: float
    avg_budget_used_pct: float
    avg_quality_score: float
    top_sources: list[dict]
    compilations_today: int


class BlockEffectiveness(BaseModel):
    source: str
    avg_quality: float
    usage_count: int
    success_rate: float
