from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PolicyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    package_path: str = Field(min_length=1, max_length=200, description="Slash-separated path, e.g. omni/policies/deploy")
    entrypoint: str = Field(default="allow", min_length=1, max_length=80)
    rego: str = Field(min_length=20)


class PolicyRecord(BaseModel):
    id: str
    name: str
    package_path: str
    entrypoint: str
    rego: str
    created_at: datetime


class PolicyDecisionRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class PolicyDecisionResponse(BaseModel):
    policy_id: str
    decision: Any
    source: str
    evaluated_at: datetime


class BundleValidationRequest(BaseModel):
    files: dict[str, str] = Field(default_factory=dict)


class BundleValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
    files_checked: int
