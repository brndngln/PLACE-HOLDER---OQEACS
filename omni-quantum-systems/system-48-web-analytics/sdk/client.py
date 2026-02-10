"""Plausible SDK client."""
from __future__ import annotations
from typing import Any
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential


logger = structlog.get_logger(__name__)


class PlausibleClient:
    def __init__(self, base_url: str, api_key: str):
        self._client = httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params); r.raise_for_status(); return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post(path, json=data); r.raise_for_status(); return r.json()

    def get_stats(self, site_id: str, period: str = "30d") -> dict[str, Any]:
        return self._get("/api/v1/stats/aggregate", site_id=site_id, period=period)

    def get_breakdown(self, site_id: str, property: str, period: str) -> dict[str, Any]:
        return self._get("/api/v1/stats/breakdown", site_id=site_id, property=property, period=period)

    def track_event(self, site_id: str, event_name: str, props: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/event", {"name": event_name, "domain": site_id, "props": props})

    def list_sites(self) -> list[dict[str, Any]]:
        return self._get("/api/v1/sites").get("results", [])
