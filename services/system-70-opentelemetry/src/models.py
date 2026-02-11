from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TraceSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    service_name: str
    operation_name: str
    start_time: datetime
    duration_ms: float
    status: str
    attributes: dict = Field(default_factory=dict)
    events: list[dict] = Field(default_factory=list)


class TraceQuery(BaseModel):
    service_name: str | None = None
    operation: str | None = None
    min_duration_ms: float | None = None
    max_duration_ms: float | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = 100


class TraceResult(BaseModel):
    traces: list[TraceSpan]
    total_count: int


class ServiceNode(BaseModel):
    name: str
    span_count: int
    avg_latency_ms: float
    error_rate: float


class ServiceConnection(BaseModel):
    source: str
    target: str
    request_count: int
    avg_latency_ms: float


class ServiceMap(BaseModel):
    services: list[ServiceNode]
    connections: list[ServiceConnection]
