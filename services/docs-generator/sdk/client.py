from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class DocsGeneratorClient:
    base_url: str = "http://localhost:9629"
    timeout_seconds: float = 30.0

    async def _request(self, method: str, path: str, json_data: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.request(method, f"{self.base_url}{path}", json=json_data)
            response.raise_for_status()
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            return response.text

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/health")

    async def info(self) -> dict[str, Any]:
        return await self._request("GET", "/info")

    async def ready(self) -> dict[str, Any]:
        return await self._request("GET", "/ready")
