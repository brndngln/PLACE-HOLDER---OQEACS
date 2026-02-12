"""Unleash SDK client."""
from __future__ import annotations
from typing import Any
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class UnleashClient:
    def __init__(self, base_url: str, api_token: str, environment: str):
        self.environment = environment
        self._client = httpx.Client(base_url=base_url, headers={"Authorization": api_token}, timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params); r.raise_for_status(); return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post(path, json=data); r.raise_for_status(); return r.json()

    def is_enabled(self, flag_name: str, context: dict[str, Any] | None = None) -> bool:
        data = self._get(f"/api/client/features/{flag_name}", environment=self.environment, **(context or {}))
        return bool(data.get("enabled", False))

    def get_variant(self, flag_name: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._get(f"/api/client/features/{flag_name}", environment=self.environment, **(context or {})).get("variant", {})

    def list_flags(self) -> list[dict[str, Any]]:
        return self._get("/api/admin/projects/default/features").get("features", [])

    def get_flag_details(self, name: str) -> dict[str, Any]:
        return self._get(f"/api/admin/projects/default/features/{name}")
