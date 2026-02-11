from __future__ import annotations

from typing import Any

import httpx


class ObservabilityOtelClient:
    def __init__(self, base_url: str = "http://omni-observability-otel:9651", timeout: float = 15.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ObservabilityOtelClient":
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

    async def pipelines(self) -> dict[str, Any]:
        r = await self.client.get(f"{self._base_url}/api/v1/pipelines")
        r.raise_for_status()
        return r.json()

    async def get_sampling(self) -> dict[str, Any]:
        r = await self.client.get(f"{self._base_url}/api/v1/pipelines/sampling")
        r.raise_for_status()
        return r.json()

    async def set_sampling(self, ratio: float) -> dict[str, Any]:
        r = await self.client.put(f"{self._base_url}/api/v1/pipelines/sampling", json={"ratio": ratio})
        r.raise_for_status()
        return r.json()

    async def instrumentation_check(self, service_url: str, endpoint: str = "/health", method: str = "GET") -> dict[str, Any]:
        r = await self.client.post(
            f"{self._base_url}/api/v1/instrumentation/check",
            json={"service_url": service_url, "endpoint": endpoint, "method": method},
        )
        r.raise_for_status()
        return r.json()

    async def collector_status(self) -> dict[str, Any]:
        r = await self.client.get(f"{self._base_url}/api/v1/collector/status")
        r.raise_for_status()
        return r.json()
