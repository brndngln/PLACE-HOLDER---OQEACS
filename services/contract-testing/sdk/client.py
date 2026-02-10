"""Pact Broker SDK client."""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class Pacticipant(BaseModel):
    name: str


class PublishResult(BaseModel):
    status: str


class DeployCheck(BaseModel):
    summary: dict[str, Any]


class ContractSummary(BaseModel):
    consumer: str
    provider: str


class VerificationResult(BaseModel):
    ok: bool
    details: dict[str, Any] = {}


class CompatibilityMatrix(BaseModel):
    matrix: list[dict[str, Any]]


class GeneratedContract(BaseModel):
    status: str
    contract: dict[str, Any]


class PactBrokerClient:
    def __init__(self, base_url: str, username: str, password: str):
        self._client = httpx.Client(base_url=base_url, auth=(username, password), timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post(path, json=data)
        r.raise_for_status()
        return r.json() if r.text else {"status": "ok"}

    def list_pacticipants(self) -> list[Pacticipant]:
        data = self._get("/pacticipants").get("_embedded", {}).get("pacticipants", [])
        return [Pacticipant(name=p["name"]) for p in data]

    def publish_contract(self, consumer: str, provider: str, contract_json: dict[str, Any], version: str) -> PublishResult:
        self._post(f"/pacts/provider/{provider}/consumer/{consumer}/version/{version}", contract_json)
        return PublishResult(status="published")

    def can_i_deploy(self, pacticipant: str, version: str, environment: str = "production") -> DeployCheck:
        return DeployCheck(summary=self._get("/can-i-deploy", pacticipant=pacticipant, version=version, to=environment))

    def list_contracts(self, consumer: str | None = None, provider: str | None = None) -> list[ContractSummary]:
        if consumer and provider:
            return [ContractSummary(consumer=consumer, provider=provider)]
        return []

    def get_verification_results(self, consumer: str, provider: str) -> VerificationResult:
        data = self._get(f"/pacts/provider/{provider}/consumer/{consumer}/latest")
        return VerificationResult(ok=True, details=data)

    def get_matrix(self, consumer: str, provider: str) -> CompatibilityMatrix:
        return CompatibilityMatrix(matrix=self._get("/matrix", q=f"consumer={consumer},provider={provider}").get("matrix", []))

    def generate_contract(self, consumer: str, provider: str) -> GeneratedContract:
        data = self._post("http://omni-contract-generator:9293/contracts/generate", {"consumer": consumer, "provider": provider})
        return GeneratedContract(**data)
