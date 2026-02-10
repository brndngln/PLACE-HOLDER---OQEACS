"""GlitchTip SDK client."""
from __future__ import annotations
from typing import Any
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class GlitchTipClient:
    def __init__(self, base_url: str, api_token: str):
        self._client = httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {api_token}"}, timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params); r.raise_for_status(); return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post(path, json=data); r.raise_for_status(); return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _put(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        r = self._client.put(path, json=data); r.raise_for_status(); return r.json()

    def list_issues(self, project: str | None = None, status: str = "unresolved") -> list[dict[str, Any]]:
        params = {"query": status}
        if project:
            params["project"] = project
        return self._get("/api/0/issues/", **params)

    def get_issue(self, issue_id: str) -> dict[str, Any]:
        return self._get(f"/api/0/issues/{issue_id}/")

    def resolve_issue(self, issue_id: str) -> dict[str, Any]:
        return self._put(f"/api/0/issues/{issue_id}/", {"status": "resolved"})

    def list_projects(self) -> list[dict[str, Any]]:
        return self._get("/api/0/projects/")

    def get_project_stats(self, project_slug: str) -> dict[str, Any]:
        return self._get(f"/api/0/projects/omni/{project_slug}/stats_v2/")
