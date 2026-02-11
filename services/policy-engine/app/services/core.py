from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from app.exceptions import ServiceError
from app.models import (
    BundleValidationRequest,
    BundleValidationResponse,
    PolicyCreateRequest,
    PolicyDecisionRequest,
    PolicyDecisionResponse,
    PolicyRecord,
)

PACKAGE_RE = re.compile(r"^package\s+[a-zA-Z0-9_.]+", re.MULTILINE)


class PolicyEngineCore:
    def __init__(self, data_path: str, policies_dir: str, opa_url: str, opa_sync_enabled: bool) -> None:
        self._data_path = Path(data_path)
        self._policies_dir = Path(policies_dir)
        self._opa_url = opa_url.rstrip("/")
        self._opa_sync_enabled = opa_sync_enabled
        self._policies: dict[str, PolicyRecord] = {}

    async def initialize(self) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        self._policies_dir.mkdir(parents=True, exist_ok=True)

        if self._data_path.exists():
            payload = json.loads(self._data_path.read_text(encoding="utf-8"))
            self._policies = {row["id"]: PolicyRecord.model_validate(row) for row in payload.get("policies", [])}

    async def _persist(self) -> None:
        payload = {"policies": [item.model_dump(mode="json") for item in self._policies.values()]}
        self._data_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    async def list_policies(self) -> list[PolicyRecord]:
        return sorted(self._policies.values(), key=lambda item: item.created_at, reverse=True)

    async def get_policy(self, policy_id: str) -> PolicyRecord:
        policy = self._policies.get(policy_id)
        if not policy:
            raise ServiceError("policy not found", status_code=404, code="policy_not_found")
        return policy

    async def create_policy(self, request: PolicyCreateRequest) -> PolicyRecord:
        self._policies_dir.mkdir(parents=True, exist_ok=True)
        self._data_path.parent.mkdir(parents=True, exist_ok=True)

        dotted = request.package_path.replace("/", ".")
        if not PACKAGE_RE.search(request.rego):
            raise ServiceError("rego policy must define a package", status_code=422, code="invalid_rego")
        if f"package {dotted}" not in request.rego:
            raise ServiceError(
                "rego package mismatch with package_path",
                status_code=422,
                code="package_mismatch",
            )

        policy = PolicyRecord(
            id=f"plc-{uuid4().hex[:12]}",
            name=request.name,
            package_path=request.package_path,
            entrypoint=request.entrypoint,
            rego=request.rego,
            created_at=datetime.now(timezone.utc),
        )
        self._policies[policy.id] = policy

        policy_path = self._policies_dir / f"{policy.id}.rego"
        policy_path.write_text(policy.rego, encoding="utf-8")

        if self._opa_sync_enabled:
            await self._sync_policy_to_opa(policy)

        await self._persist()
        return policy

    async def _sync_policy_to_opa(self, policy: PolicyRecord) -> None:
        url = f"{self._opa_url}/v1/policies/{policy.id}"
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.put(url, content=policy.rego, headers={"Content-Type": "text/plain"})
        if response.status_code >= 400:
            raise ServiceError(
                f"OPA sync failed with status={response.status_code}",
                status_code=502,
                code="opa_sync_failed",
            )

    async def evaluate(self, policy_id: str, request: PolicyDecisionRequest) -> PolicyDecisionResponse:
        policy = await self.get_policy(policy_id)

        if self._opa_sync_enabled:
            path = policy.package_path.strip("/") + "/" + policy.entrypoint
            url = f"{self._opa_url}/v1/data/{path}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(url, json={"input": request.input})
            if response.status_code >= 400:
                raise ServiceError("OPA decision API failed", status_code=502, code="opa_evaluation_failed")
            decision = response.json().get("result")
            source = "opa"
        else:
            decision = bool(request.input.get("allow", False))
            source = "local"

        return PolicyDecisionResponse(
            policy_id=policy_id,
            decision=decision,
            source=source,
            evaluated_at=datetime.now(timezone.utc),
        )

    async def validate_bundle(self, request: BundleValidationRequest) -> BundleValidationResponse:
        errors: list[str] = []
        for path, content in request.files.items():
            if not path.endswith(".rego"):
                errors.append(f"{path}: expected .rego extension")
            if not PACKAGE_RE.search(content):
                errors.append(f"{path}: missing package declaration")
            if "default" not in content:
                errors.append(f"{path}: missing default rule")
        return BundleValidationResponse(valid=not errors, errors=errors, files_checked=len(request.files))

    async def opa_status(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(f"{self._opa_url}/health")
            if response.status_code >= 400:
                return {"healthy": False, "detail": f"status={response.status_code}"}
            return {"healthy": True, "detail": "ok"}
        except Exception as exc:
            return {"healthy": False, "detail": str(exc)}
