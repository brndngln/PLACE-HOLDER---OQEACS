import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class CrossLearningClient:
    def __init__(self, base_url: str = "http://omni-cross-learning:8332", api_token: str = ""):
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

    def get_insights(self, project_id: str) -> dict:
        """Get cross-learning insights for a specific project."""
        logger.info("getting_insights", project_id=project_id)
        return self._get(f"/api/v1/projects/{project_id}/insights")

    def list_patterns(self) -> dict:
        """List all discovered cross-project patterns."""
        logger.info("listing_patterns")
        return self._get("/api/v1/patterns")

    def apply_learning(self, source_project: str, target_project: str) -> dict:
        """Apply learnings from a source project to a target project."""
        logger.info("applying_learning", source=source_project, target=target_project)
        return self._post("/api/v1/apply", {
            "source_project": source_project,
            "target_project": target_project,
        })

    def get_report(self) -> dict:
        """Get the aggregate cross-learning report."""
        logger.info("getting_report")
        return self._get("/api/v1/reports")
