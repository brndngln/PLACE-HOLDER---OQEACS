import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class MCPDocsClient:
    def __init__(self, base_url: str = "http://omni-mcp-docs:8327", api_token: str = ""):
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

    def search_docs(self, query: str, framework: str | None = None) -> dict:
        """Search documentation by query, optionally scoped to a framework."""
        params = {"query": query}
        if framework is not None:
            params["framework"] = framework
        logger.info("searching_docs", query=query, framework=framework)
        return self._get("/api/v1/docs/search", **params)

    def get_doc(self, id: str) -> dict:
        """Get a specific documentation entry by its ID."""
        logger.info("getting_doc", doc_id=id)
        return self._get(f"/api/v1/docs/{id}")

    def list_frameworks(self) -> dict:
        """List all available documentation frameworks."""
        logger.info("listing_frameworks")
        return self._get("/api/v1/frameworks")
