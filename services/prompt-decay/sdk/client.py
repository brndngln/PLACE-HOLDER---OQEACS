import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class PromptDecayClient:
    def __init__(self, base_url: str = "http://omni-prompt-decay:8331", api_token: str = ""):
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

    def check_decay(self, prompt_id: str) -> dict:
        """Check the decay status of a specific prompt."""
        logger.info("checking_decay", prompt_id=prompt_id)
        return self._get(f"/api/v1/prompts/{prompt_id}/decay")

    def list_prompts(self, status: str | None = None) -> dict:
        """List all tracked prompts, optionally filtered by status."""
        params = {}
        if status is not None:
            params["status"] = status
        logger.info("listing_prompts", status=status)
        return self._get("/api/v1/prompts", **params)

    def get_decay_report(self) -> dict:
        """Get the aggregate decay report across all prompts."""
        logger.info("getting_decay_report")
        return self._get("/api/v1/reports/decay")

    def mark_refreshed(self, prompt_id: str) -> dict:
        """Mark a prompt as refreshed, resetting its decay timer."""
        logger.info("marking_refreshed", prompt_id=prompt_id)
        return self._post(f"/api/v1/prompts/{prompt_id}/refresh", {})
