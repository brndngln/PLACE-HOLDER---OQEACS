import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class ObservatoryClient:
    """SDK client for the Observatory service (Prometheus API)."""

    def __init__(
        self,
        base_url: str = "http://omni-prometheus:9090/api/v1",
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

    def query(self, promql: str) -> dict:
        """Execute an instant PromQL query."""
        logger.info("observatory.query", promql=promql)
        return self._get("/query", query=promql)

    def query_range(
        self, promql: str, start: str, end: str, step: str
    ) -> dict:
        """Execute a range PromQL query."""
        logger.info(
            "observatory.query_range",
            promql=promql,
            start=start,
            end=end,
            step=step,
        )
        return self._get(
            "/query_range", query=promql, start=start, end=end, step=step
        )

    def list_alerts(self) -> dict:
        """List all active alerts."""
        logger.info("observatory.list_alerts")
        return self._get("/alerts")

    def get_targets(self) -> dict:
        """Get all scrape targets and their current status."""
        logger.info("observatory.get_targets")
        return self._get("/targets")

    def get_rules(self) -> dict:
        """Get all configured alerting and recording rules."""
        logger.info("observatory.get_rules")
        return self._get("/rules")
