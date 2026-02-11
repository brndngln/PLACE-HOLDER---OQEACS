'''Async SDK client for omni-patch-tree.'''
from __future__ import annotations

from typing import Any

import httpx


class PatchTreeClient:
    '''Simple async SDK client for inter-service communication.'''

    def __init__(self, base_url: str = "http://omni-patch-tree:9852", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method=method.upper(), url=f"{self.base_url}{path}", json=payload)
            response.raise_for_status()
            return response.json()

    async def primary(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.request("POST", "/api/v1/search/start", payload or {})
