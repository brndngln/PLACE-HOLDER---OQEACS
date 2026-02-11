import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class MCPPipelineClient:
    def __init__(self, base_url: str = "http://omni-mcp-pipeline:8329", api_token: str = ""):
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

    def list_pipelines(self) -> dict:
        """List all available pipelines."""
        logger.info("listing_pipelines")
        return self._get("/api/v1/pipelines")

    def get_pipeline(self, id: str) -> dict:
        """Get details of a specific pipeline by its ID."""
        logger.info("getting_pipeline", pipeline_id=id)
        return self._get(f"/api/v1/pipelines/{id}")

    def trigger_pipeline(self, id: str, params: dict | None = None) -> dict:
        """Trigger a pipeline execution with optional parameters."""
        payload = {}
        if params is not None:
            payload["params"] = params
        logger.info("triggering_pipeline", pipeline_id=id, has_params=params is not None)
        return self._post(f"/api/v1/pipelines/{id}/trigger", payload)

    def get_pipeline_status(self, id: str) -> dict:
        """Get the current execution status of a pipeline."""
        logger.info("getting_pipeline_status", pipeline_id=id)
        return self._get(f"/api/v1/pipelines/{id}/status")
