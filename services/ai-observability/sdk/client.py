import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class LangfuseClient:
    """SDK client for the AI-Observability service (Langfuse API)."""

    def __init__(
        self,
        base_url: str = "http://omni-langfuse:3000/api/public",
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

    def list_traces(self, limit: int = 50) -> dict:
        """List recent traces, capped at the given limit."""
        logger.info("langfuse.list_traces", limit=limit)
        return self._get("/traces", limit=limit)

    def get_trace(self, id: str) -> dict:
        """Get a single trace by its ID."""
        logger.info("langfuse.get_trace", trace_id=id)
        return self._get(f"/traces/{id}")

    def list_scores(self, trace_id: str | None = None) -> dict:
        """List scores, optionally filtered by trace ID."""
        logger.info("langfuse.list_scores", trace_id=trace_id)
        params: dict = {}
        if trace_id is not None:
            params["traceId"] = trace_id
        return self._get("/scores", **params)

    def create_score(self, trace_id: str, name: str, value: float) -> dict:
        """Create a new score for the specified trace."""
        logger.info(
            "langfuse.create_score",
            trace_id=trace_id,
            name=name,
            value=value,
        )
        return self._post(
            "/scores",
            data={"traceId": trace_id, "name": name, "value": value},
        )

    def list_prompts(self) -> dict:
        """List all registered prompts."""
        logger.info("langfuse.list_prompts")
        return self._get("/prompts")
