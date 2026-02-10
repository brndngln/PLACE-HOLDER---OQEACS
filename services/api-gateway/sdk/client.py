"""Kong admin SDK client."""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class ServiceInfo(BaseModel):
    id: str
    name: str
    host: str | None = None


class RouteInfo(BaseModel):
    id: str
    name: str | None = None


class ConsumerInfo(BaseModel):
    id: str
    username: str


class PluginInfo(BaseModel):
    id: str
    name: str


class KongStatus(BaseModel):
    database: dict[str, Any] | None = None
    server: dict[str, Any] | None = None


class KongAdminClient:
    def __init__(self, admin_url: str = "http://localhost:8001", api_token: str | None = None):
        headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}
        self._client = httpx.Client(base_url=admin_url, headers=headers, timeout=30.0)

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

    def list_services(self) -> list[ServiceInfo]:
        return [ServiceInfo(**i) for i in self._get("/services").get("data", [])]

    def create_service(self, name: str, url: str, **kwargs: Any) -> ServiceInfo:
        return ServiceInfo(**self._post("/services", {"name": name, "url": url, **kwargs}))

    def list_routes(self, service_id: str | None = None) -> list[RouteInfo]:
        path = f"/services/{service_id}/routes" if service_id else "/routes"
        return [RouteInfo(**i) for i in self._get(path).get("data", [])]

    def create_route(self, service_id: str, paths: list[str], methods: list[str] | None = None, **kwargs: Any) -> RouteInfo:
        payload = {"paths": paths, **({"methods": methods} if methods else {}), **kwargs}
        return RouteInfo(**self._post(f"/services/{service_id}/routes", payload))

    def list_consumers(self) -> list[ConsumerInfo]:
        return [ConsumerInfo(**i) for i in self._get("/consumers").get("data", [])]

    def create_consumer(self, username: str, group: str) -> ConsumerInfo:
        return ConsumerInfo(**self._post("/consumers", {"username": username, "custom_id": group}))

    def create_api_key(self, consumer_id: str) -> dict[str, Any]:
        return self._post(f"/consumers/{consumer_id}/key-auth", {})

    def list_plugins(self) -> list[PluginInfo]:
        return [PluginInfo(**i) for i in self._get("/plugins").get("data", [])]

    def add_plugin(self, name: str, config: dict[str, Any], service_id: str | None = None, route_id: str | None = None) -> PluginInfo:
        target = "/plugins"
        if route_id:
            target = f"/routes/{route_id}/plugins"
        elif service_id:
            target = f"/services/{service_id}/plugins"
        return PluginInfo(**self._post(target, {"name": name, "config": config}))

    def get_status(self) -> KongStatus:
        return KongStatus(**self._get("/status"))

    def get_metrics(self) -> str:
        r = self._client.get("http://omni-kong:8100/metrics")
        r.raise_for_status()
        return r.text
