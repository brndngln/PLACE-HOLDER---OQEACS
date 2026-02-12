from __future__ import annotations
from typing import Any
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class TolgeeClient:
    def __init__(self, base_url: str, api_key: str):
        self._client = httpx.Client(base_url=base_url, headers={"X-API-Key": api_key}, timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params); r.raise_for_status(); return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: Any) -> dict[str, Any]:
        r = self._client.post(path, json=data); r.raise_for_status(); return r.json()

    def list_projects(self) -> list[dict[str, Any]]:
        return self._get("/v2/projects").get("_embedded", {}).get("projects", [])

    def get_translations(self, project_id: int, language: str) -> dict[str, Any]:
        return self._get(f"/v2/projects/{project_id}/translations", languages=language)

    def create_key(self, project_id: int, key_name: str, translations: dict[str, str]) -> dict[str, Any]:
        return self._post(f"/v2/projects/{project_id}/keys", {"name": key_name, "translations": translations})

    def update_translation(self, project_id: int, key_id: int, language: str, value: str) -> dict[str, Any]:
        return self._post(f"/v2/projects/{project_id}/translations", {"keyId": key_id, "languageTag": language, "translation": value})

    def export_translations(self, project_id: int, format: str = "json") -> bytes:
        r = self._client.get(f"/v2/projects/{project_id}/export", params={"format": format}); r.raise_for_status(); return r.content

    def import_translations(self, project_id: int, file: bytes) -> dict[str, Any]:
        r = self._client.post(f"/v2/projects/{project_id}/import", files={"file": ("translations.json", file, "application/json")}); r.raise_for_status(); return r.json()
