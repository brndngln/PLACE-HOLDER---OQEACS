import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class PlaneClient:
    def __init__(
        self,
        base_url: str = "http://omni-plane-web:3000/api/v1",
        api_token: str = "",
        workspace: str = "omni-quantum",
    ):
        self._workspace = workspace
        self._client = httpx.Client(
            base_url=f"{base_url}/workspaces/{workspace}",
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=30.0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params) -> dict:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict) -> dict:
        r = self._client.post(path, json=data)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _patch(self, path: str, data: dict) -> dict:
        r = self._client.patch(path, json=data)
        r.raise_for_status()
        return r.json()

    def list_projects(self) -> list:
        return self._get("/projects/").get("results", [])

    def create_project(self, template: str, name: str, **kw) -> dict:
        payload = {"name": name, "template": template, **kw}
        return self._post("/projects/", payload)

    def list_issues(self, project_id: str, filters: dict | None = None) -> list:
        params = filters or {}
        return self._get(f"/projects/{project_id}/issues/", **params).get("results", [])

    def create_issue(self, project_id: str, title: str, desc: str, **kw) -> dict:
        payload = {"name": title, "description": desc, **kw}
        return self._post(f"/projects/{project_id}/issues/", payload)

    def update_issue(self, project_id: str, issue_id: str, **kw) -> dict:
        return self._patch(f"/projects/{project_id}/issues/{issue_id}/", kw)

    def list_modules(self, project_id: str) -> list:
        return self._get(f"/projects/{project_id}/modules/").get("results", [])

    def get_project_stats(self, project_id: str) -> dict:
        issues = self.list_issues(project_id)
        state_counts = {}
        for iss in issues:
            state = iss.get("state", {}).get("name", "Unknown")
            state_counts[state] = state_counts.get(state, 0) + 1
        return {
            "project_id": project_id,
            "total_issues": len(issues),
            "by_state": state_counts,
        }
