from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ProvenanceCreateRequest(BaseModel):
    artifact_name: str = Field(min_length=1, max_length=300)
    digest_sha256: str = Field(pattern="^[a-fA-F0-9]{64}$")
    build_type: str = Field(default="https://slsa.dev/container-based-build/v1")
    builder_id: str | None = None
    invocation: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttestationRecord(BaseModel):
    id: str
    statement: dict[str, Any]
    created_at: datetime
    signature: str | None = None


class SignatureResponse(BaseModel):
    attestation_id: str
    signature: str
    algorithm: Literal["hmac-sha256"]


class VerifyRequest(BaseModel):
    signature: str = Field(min_length=10)


class VerifyResponse(BaseModel):
    attestation_id: str
    verified: bool
    detail: str


class SbomIngestRequest(BaseModel):
    format: Literal["spdx", "cyclonedx"]
    document: dict[str, Any]


class SbomRecord(BaseModel):
    id: str
    format: str
    document: dict[str, Any]
    created_at: datetime


class SbomVerifyResponse(BaseModel):
    sbom_id: str
    valid: bool
    errors: list[str]


class HubStats(BaseModel):
    attestations_total: int
    signed_total: int
    sboms_total: int
