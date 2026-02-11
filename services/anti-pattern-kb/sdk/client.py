import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class AntiPatternClient:
    def __init__(self, base_url: str = "http://omni-anti-pattern-kb:8330", api_token: str = ""):
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

    def search_patterns(self, query: str, language: str | None = None) -> dict:
        """Search for known anti-patterns matching the query."""
        params = {"query": query}
        if language is not None:
            params["language"] = language
        logger.info("searching_patterns", query=query, language=language)
        return self._get("/api/v1/patterns/search", **params)

    def get_pattern(self, id: str) -> dict:
        """Get details of a specific anti-pattern by its ID."""
        logger.info("getting_pattern", pattern_id=id)
        return self._get(f"/api/v1/patterns/{id}")

    def list_categories(self) -> dict:
        """List all anti-pattern categories."""
        logger.info("listing_categories")
        return self._get("/api/v1/categories")

    def detect_patterns(self, code: str, language: str) -> dict:
        """Detect anti-patterns in the provided code snippet."""
        logger.info("detecting_patterns", language=language)
        return self._post("/api/v1/detect", {"code": code, "language": language})
