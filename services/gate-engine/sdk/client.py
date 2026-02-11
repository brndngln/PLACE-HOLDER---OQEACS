import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class GateEngineClient:
    def __init__(self, base_url: str = "http://omni-gate-engine:8351", api_token: str = ""):
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

    def evaluate(self, artifact_id: str, tier: str, metadata: dict | None = None) -> dict:
        """Evaluate an artifact against a quality gate at the specified tier."""
        payload = {"artifact_id": artifact_id, "tier": tier}
        if metadata is not None:
            payload["metadata"] = metadata
        logger.info("evaluating_artifact", artifact_id=artifact_id, tier=tier)
        return self._post("/api/v1/evaluate", payload)

    def get_gate_status(self, artifact_id: str) -> dict:
        """Get the current gate status for a given artifact."""
        logger.info("getting_gate_status", artifact_id=artifact_id)
        return self._get(f"/api/v1/gates/{artifact_id}/status")

    def list_evaluations(self, status: str | None = None) -> dict:
        """List all evaluations, optionally filtered by status."""
        logger.info("listing_evaluations", status=status)
        params = {}
        if status is not None:
            params["status"] = status
        return self._get("/api/v1/evaluations", **params)
