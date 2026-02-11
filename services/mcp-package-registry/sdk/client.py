import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class MCPPackageRegistryClient:
    def __init__(self, base_url: str = "http://omni-mcp-package-registry:8326", api_token: str = ""):
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

    def search_packages(self, query: str, language: str | None = None) -> dict:
        """Search for packages matching the given query string."""
        params = {"query": query}
        if language is not None:
            params["language"] = language
        logger.info("searching_packages", query=query, language=language)
        return self._get("/api/v1/packages/search", **params)

    def get_package(self, name: str, version: str | None = None) -> dict:
        """Get details for a specific package, optionally at a specific version."""
        params = {}
        if version is not None:
            params["version"] = version
        logger.info("getting_package", name=name, version=version)
        return self._get(f"/api/v1/packages/{name}", **params)

    def list_packages(self, language: str | None = None) -> dict:
        """List all available packages, optionally filtered by language."""
        params = {}
        if language is not None:
            params["language"] = language
        logger.info("listing_packages", language=language)
        return self._get("/api/v1/packages", **params)
