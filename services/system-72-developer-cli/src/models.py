from __future__ import annotations

from pydantic import BaseModel, Field


class CLICommand(BaseModel):
    name: str
    description: str
    arguments: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class CommandResult(BaseModel):
    command: str
    success: bool
    output: str
    duration_ms: float
    error: str | None = None


class ServiceStatus_(BaseModel):
    name: str
    port: int
    healthy: bool
    response_time_ms: float


class PlatformStatus(BaseModel):
    total_services: int
    healthy_services: int
    unhealthy_services: int
    services: list[ServiceStatus_]


class GenerateRequest(BaseModel):
    description: str
    language: str
    output_path: str


class ReviewRequest(BaseModel):
    file_path: str
    focus_areas: list[str] = Field(default_factory=list)
