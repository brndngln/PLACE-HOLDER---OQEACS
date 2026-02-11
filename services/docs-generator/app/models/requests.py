from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class GenericRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class CreateItemRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    data: dict[str, Any] = Field(default_factory=dict)


class ExecuteRequest(BaseModel):
    command: str | None = Field(default=None, max_length=10_000)
    code: str | None = Field(default=None, max_length=1_000_000)
    timeout_seconds: int = Field(default=30, ge=1, le=600)

    @model_validator(mode="after")
    def _validate_command_or_code(self) -> "ExecuteRequest":
        if bool(self.command) == bool(self.code):
            raise ValueError("Exactly one of command or code must be provided")
        return self


class CreateAnalysisRequest(BaseModel):
    repo_url: str | None = None
    local_path: str | None = None
    git_ref: str = "main"
    depth: str = "full"
    force_reanalyze: bool = False

    @model_validator(mode="after")
    def _validate_source(self) -> "CreateAnalysisRequest":
        if bool(self.repo_url) == bool(self.local_path):
            raise ValueError("Exactly one of repo_url or local_path is required")
        return self


class ScanRequest(BaseModel):
    code: str = Field(min_length=1, max_length=1_000_000)
    language: str
    dependencies: dict[str, str] = Field(default_factory=dict)
    spec_summary: str | None = None
    model_used: str | None = None
    task_id: str | None = None
    checks: list[str] | None = None
