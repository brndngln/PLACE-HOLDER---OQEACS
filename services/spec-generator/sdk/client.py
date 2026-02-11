import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class SpecGeneratorClient:
    def __init__(self, base_url: str = "http://omni-spec-generator:8333", api_token: str = ""):
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

    def generate_spec(self, description: str, type: str = "api") -> dict:
        """Generate a specification from a natural-language description."""
        logger.info("generating_spec", type=type)
        return self._post("/api/v1/specs/generate", {
            "description": description,
            "type": type,
        })

    def get_spec(self, id: str) -> dict:
        """Get a specific generated specification by its ID."""
        logger.info("getting_spec", spec_id=id)
        return self._get(f"/api/v1/specs/{id}")

    def list_specs(self) -> dict:
        """List all generated specifications."""
        logger.info("listing_specs")
        return self._get("/api/v1/specs")

    def validate_spec(self, spec_content: str) -> dict:
        """Validate a specification's content for correctness."""
        logger.info("validating_spec")
        return self._post("/api/v1/specs/validate", {"spec_content": spec_content})
