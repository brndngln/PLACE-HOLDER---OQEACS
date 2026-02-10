import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class CoolifyClient:
    def __init__(
        self,
        base_url: str = "http://omni-coolify:8000/api/v1",
        api_token: str = "",
    ):
        self._client = httpx.Client(
            base_url=base_url,
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

    def list_applications(self) -> list:
        return self._get("/applications").get("data", [])

    def create_application(self, template: str, name: str, repo_url: str, **kw) -> dict:
        payload = {"template": template, "name": name, "git_repository": repo_url, **kw}
        return self._post("/applications", payload)

    def deploy(self, app_id: str, env: str = "staging") -> dict:
        return self._post(f"/applications/{app_id}/deploy", {"environment": env})

    def rollback(self, app_id: str, version: str) -> dict:
        return self._post(f"/applications/{app_id}/rollback", {"version": version})

    def get_deploy_status(self, app_id: str) -> dict:
        return self._get(f"/applications/{app_id}/deploy/status")

    def get_deploy_logs(self, app_id: str, deploy_id: str) -> dict:
        return self._get(f"/applications/{app_id}/deployments/{deploy_id}/logs")

    def list_deployments(self, app_id: str) -> list:
        return self._get(f"/applications/{app_id}/deployments").get("data", [])

    def get_application_metrics(self, app_id: str) -> dict:
        return self._get(f"/applications/{app_id}/metrics")
