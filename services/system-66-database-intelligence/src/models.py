from __future__ import annotations

from pydantic import BaseModel, Field


class IndexRecommendation(BaseModel):
    table: str
    columns: list[str]
    type: str
    reason: str
    estimated_improvement: str


class SchemaReview(BaseModel):
    tables: list[str]
    issues: list[str] = Field(default_factory=list)
    score: float
    recommendations: list[str] = Field(default_factory=list)


class QueryAnalysis(BaseModel):
    query: str
    execution_plan_summary: str
    estimated_cost: float
    suggestions: list[str] = Field(default_factory=list)
    index_recommendations: list[IndexRecommendation] = Field(default_factory=list)


class MigrationSafety(BaseModel):
    migration_sql: str
    safe: bool
    risks: list[str] = Field(default_factory=list)
    estimated_lock_time: str
    rollback_plan: str
