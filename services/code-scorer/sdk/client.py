import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class CodeScorerClient:
    def __init__(self, base_url: str = "http://omni-code-scorer:8350", api_token: str = ""):
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

    def score_code(self, code: str, language: str, context: str | None = None) -> dict:
        """Score a code snippet for quality across multiple dimensions."""
        payload = {"code": code, "language": language}
        if context is not None:
            payload["context"] = context
        logger.info("scoring_code", language=language, has_context=context is not None)
        return self._post("/api/v1/score", payload)

    def get_scoring_dimensions(self) -> dict:
        """Retrieve the available scoring dimensions and their descriptions."""
        logger.info("getting_scoring_dimensions")
        return self._get("/api/v1/dimensions")

    def batch_score(self, items: list[dict]) -> dict:
        """Score multiple code items in a single batch request."""
        logger.info("batch_scoring", item_count=len(items))
        return self._post("/api/v1/score/batch", {"items": items})
