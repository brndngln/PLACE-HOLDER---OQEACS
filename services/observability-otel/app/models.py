from datetime import datetime
from pydantic import BaseModel, Field


class SamplingPolicy(BaseModel):
    ratio: float = Field(ge=0.0, le=1.0)
    updated_at: datetime


class InstrumentationCheckRequest(BaseModel):
    service_url: str = Field(min_length=8, max_length=500)
    endpoint: str = Field(default="/health", min_length=1, max_length=200)
    method: str = Field(default="GET", pattern="^(GET|POST|PUT|DELETE|PATCH)$")


class InstrumentationCheckResult(BaseModel):
    service_url: str
    endpoint: str
    status_code: int
    has_trace_context: bool
    latency_ms: float


class CollectorStatus(BaseModel):
    healthy: bool
    detail: str
