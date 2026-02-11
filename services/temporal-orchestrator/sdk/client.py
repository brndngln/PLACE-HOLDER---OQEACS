from __future__ import annotations

from typing import Any

import httpx


class TemporalOrchestratorClient:
    def __init__(self, base_url: str = "http://omni-temporal-orchestrator:9650", timeout: float = 20.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "TemporalOrchestratorClient":
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def create_definition(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = await self.client.post(f"{self._base_url}/api/v1/workflows/definitions", json=payload)
        r.raise_for_status()
        return r.json()

    async def list_definitions(self) -> list[dict[str, Any]]:
        r = await self.client.get(f"{self._base_url}/api/v1/workflows/definitions")
        r.raise_for_status()
        return r.json()

    async def start_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        r = await self.client.post(f"{self._base_url}/api/v1/workflows/runs", json=payload)
        r.raise_for_status()
        return r.json()

    async def get_run(self, run_id: str) -> dict[str, Any]:
        r = await self.client.get(f"{self._base_url}/api/v1/workflows/runs/{run_id}")
        r.raise_for_status()
        return r.json()

    async def signal_run(self, run_id: str, signal_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        r = await self.client.post(
            f"{self._base_url}/api/v1/workflows/runs/{run_id}/signal",
            json={"signal_name": signal_name, "payload": payload or {}},
        )
        r.raise_for_status()
        return r.json()

    async def terminate_run(self, run_id: str) -> dict[str, Any]:
        r = await self.client.post(f"{self._base_url}/api/v1/workflows/runs/{run_id}/terminate")
        r.raise_for_status()
        return r.json()

    async def stats(self) -> dict[str, Any]:
        r = await self.client.get(f"{self._base_url}/api/v1/workflows/stats")
        r.raise_for_status()
        return r.json()
