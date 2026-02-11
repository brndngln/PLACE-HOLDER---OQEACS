from __future__ import annotations

from typing import Any

import httpx


class PolicyEngineClient:
    def __init__(self, base_url: str = "http://omni-policy-engine:9652", timeout: float = 15.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "PolicyEngineClient":
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def create_policy(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = await self.client.post(f"{self._base_url}/api/v1/policies", json=payload)
        r.raise_for_status()
        return r.json()

    async def list_policies(self) -> list[dict[str, Any]]:
        r = await self.client.get(f"{self._base_url}/api/v1/policies")
        r.raise_for_status()
        return r.json()

    async def evaluate(self, policy_id: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        r = await self.client.post(f"{self._base_url}/api/v1/decisions/{policy_id}", json={"input": input_payload})
        r.raise_for_status()
        return r.json()

    async def validate_bundle(self, files: dict[str, str]) -> dict[str, Any]:
        r = await self.client.post(f"{self._base_url}/api/v1/bundles/validate", json={"files": files})
        r.raise_for_status()
        return r.json()

    async def opa_status(self) -> dict[str, Any]:
        r = await self.client.get(f"{self._base_url}/api/v1/opa/status")
        r.raise_for_status()
        return r.json()
