"""Toxiproxy SDK client."""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class ProxyInfo(BaseModel):
    name: str
    listen: str
    upstream: str


class Toxic(BaseModel):
    name: str
    type: str


class ProxyDetail(BaseModel):
    name: str
    listen: str
    upstream: str
    enabled: bool = True


class ScenarioReport(BaseModel):
    scenario: str
    status: str
    details: dict[str, Any]


class ToxiproxyClient:
    def __init__(self, base_url: str = "http://localhost:8474"):
        self._client = httpx.Client(base_url=base_url, timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post(path, json=data)
        r.raise_for_status()
        return r.json() if r.text else {}

    def list_proxies(self) -> list[ProxyInfo]:
        data = self._get("/proxies")
        return [ProxyInfo(name=k, listen=v["listen"], upstream=v["upstream"]) for k, v in data.items()]

    def create_proxy(self, name: str, listen: str, upstream: str) -> ProxyInfo:
        data = self._post("/proxies", {"name": name, "listen": listen, "upstream": upstream})
        return ProxyInfo(name=data["name"], listen=data["listen"], upstream=data["upstream"])

    def add_toxic(self, proxy_name: str, toxic_type: str, attributes: dict[str, Any]) -> Toxic:
        data = self._post(f"/proxies/{proxy_name}/toxics", {"name": f"{toxic_type}-{proxy_name}", "type": toxic_type, "stream": "downstream", "attributes": attributes})
        return Toxic(name=data["name"], type=data["type"])

    def remove_toxic(self, proxy_name: str, toxic_name: str) -> bool:
        r = self._client.delete(f"/proxies/{proxy_name}/toxics/{toxic_name}")
        return r.status_code < 300

    def reset_all(self) -> bool:
        for p in self.list_proxies():
            details = self._get(f"/proxies/{p.name}")
            for t in details.get("toxics", []):
                self.remove_toxic(p.name, t["name"])
        return True

    def get_proxy(self, name: str) -> ProxyDetail:
        d = self._get(f"/proxies/{name}")
        return ProxyDetail(**d)

    def run_scenario(self, scenario_name: str, target_service: str) -> ScenarioReport:
        return ScenarioReport(scenario=scenario_name, status="queued", details={"target": target_service})
