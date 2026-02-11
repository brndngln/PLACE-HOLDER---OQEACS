import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class IntentVerifierClient:
    def __init__(self, base_url: str = "http://omni-intent-verifier:8352", api_token: str = ""):
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

    def verify_intent(self, code: str, spec: str, context: str | None = None) -> dict:
        """Verify that code matches the declared intent/specification."""
        payload = {"code": code, "spec": spec}
        if context is not None:
            payload["context"] = context
        logger.info("verifying_intent", has_context=context is not None)
        return self._post("/api/v1/verify", payload)

    def get_verification(self, id: str) -> dict:
        """Get details of a specific verification by its ID."""
        logger.info("getting_verification", verification_id=id)
        return self._get(f"/api/v1/verifications/{id}")

    def list_verifications(self, status: str | None = None) -> dict:
        """List all verifications, optionally filtered by status."""
        logger.info("listing_verifications", status=status)
        params = {}
        if status is not None:
            params["status"] = status
        return self._get("/api/v1/verifications", **params)
