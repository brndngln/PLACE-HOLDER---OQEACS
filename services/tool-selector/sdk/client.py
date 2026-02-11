import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class ToolSelectorClient:
    def __init__(self, base_url: str = "http://omni-tool-selector:8326", api_token: str = ""):
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

    def select_tools(self, task_description: str, available_tools: list[str] | None = None) -> dict:
        """Select the best tools for a given task description."""
        payload = {"task_description": task_description}
        if available_tools is not None:
            payload["available_tools"] = available_tools
        logger.info("selecting_tools", tool_count=len(available_tools) if available_tools else 0)
        return self._post("/api/v1/select", payload)

    def get_recommendation(self, id: str) -> dict:
        """Get a specific tool recommendation by its ID."""
        logger.info("getting_recommendation", recommendation_id=id)
        return self._get(f"/api/v1/recommendations/{id}")

    def list_recommendations(self) -> dict:
        """List all tool recommendations."""
        logger.info("listing_recommendations")
        return self._get("/api/v1/recommendations")
