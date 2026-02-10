"""Bencher runner SDK client."""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class BencherClient:
    def __init__(self, base_url: str = "http://localhost:3001"):
        self._client = httpx.Client(base_url=base_url, timeout=120.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post(path, json=data)
        r.raise_for_status()
        return r.json()

    def run_benchmark(self, service_name: str, version: str | None = None) -> dict[str, Any]:
        return self._post(f"/benchmark/service/{service_name}", {"version": version})

    def compare_versions(self, service: str, baseline: str, candidate: str) -> dict[str, Any]:
        return self._post("/benchmark/compare", {"service": service, "baseline_version": baseline, "candidate_version": candidate})

    def get_history(self, service: str, days: int = 30) -> list[dict[str, Any]]:
        return self._get(f"/benchmark/history/{service}", days=days).get("history", [])

    def get_regressions(self) -> list[dict[str, Any]]:
        return self._get("/benchmark/regressions").get("regressions", [])
