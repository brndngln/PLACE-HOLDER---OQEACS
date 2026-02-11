from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkflowDefinitionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    task_queue: str = Field(min_length=1, max_length=120)
    workflow_type: str = Field(min_length=1, max_length=160)
    input_schema: dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinition(BaseModel):
    id: str
    name: str
    task_queue: str
    workflow_type: str
    input_schema: dict[str, Any]
    created_at: datetime


class WorkflowStartRequest(BaseModel):
    definition_id: str = Field(min_length=6)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=600, ge=10, le=86400)


class WorkflowSignalRequest(BaseModel):
    signal_name: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowRun(BaseModel):
    id: str
    definition_id: str
    status: Literal["queued", "running", "completed", "failed", "terminated"]
    input_payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    signals: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None


class WorkflowStats(BaseModel):
    total_definitions: int
    total_runs: int
    running_runs: int
    completed_runs: int
    failed_runs: int
