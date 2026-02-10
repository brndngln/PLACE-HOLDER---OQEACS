from __future__ import annotations

from typing import Any

import httpx


class VerdaccioClient:
    def __init__(self, base_url: str, auth_token: str, timeout: float = 20.0) -> None:
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout, headers={"Authorization": f"Bearer {auth_token}"}
        )

    def list_packages(self, scope: str = "@omni") -> list[dict[str, Any]]:
        resp = self.client.get(f"/-/v1/search?text={scope}")
        resp.raise_for_status()
        return resp.json().get("objects", [])

    def get_package(self, name: str) -> dict[str, Any]:
        resp = self.client.get(f"/{name}")
        resp.raise_for_status()
        return resp.json()

    def search(self, query: str) -> list[dict[str, Any]]:
        resp = self.client.get(f"/-/v1/search?text={query}")
        resp.raise_for_status()
        return resp.json().get("objects", [])

    def get_package_versions(self, name: str) -> list[str]:
        pkg = self.get_package(name)
        return sorted((pkg.get("versions") or {}).keys())
