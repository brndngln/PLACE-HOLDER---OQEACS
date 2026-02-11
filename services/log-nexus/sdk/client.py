import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class LogNexusClient:
    """SDK client for the Log-Nexus service (Loki API)."""

    def __init__(
        self,
        base_url: str = "http://omni-loki:3100",
        api_token: str = "",
    ):
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

    # ── Public methods ──────────────────────────────────────────────

    def query(self, logql: str) -> dict:
        """Execute an instant LogQL query."""
        logger.info("lognexus.query", logql=logql)
        return self._get("/loki/api/v1/query", query=logql)

    def query_range(self, logql: str, start: str, end: str) -> dict:
        """Execute a range LogQL query."""
        logger.info(
            "lognexus.query_range", logql=logql, start=start, end=end
        )
        return self._get(
            "/loki/api/v1/query_range", query=logql, start=start, end=end
        )

    def list_labels(self) -> dict:
        """List all known label names."""
        logger.info("lognexus.list_labels")
        return self._get("/loki/api/v1/labels")

    def label_values(self, label: str) -> dict:
        """List all known values for a given label."""
        logger.info("lognexus.label_values", label=label)
        return self._get(f"/loki/api/v1/label/{label}/values")

    def tail(self, logql: str, limit: int = 100) -> dict:
        """Tail live log entries matching the given LogQL query."""
        logger.info("lognexus.tail", logql=logql, limit=limit)
        return self._get("/loki/api/v1/tail", query=logql, limit=limit)
