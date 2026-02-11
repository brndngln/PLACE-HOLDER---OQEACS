import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class N8nClient:
    """SDK client for the Workflow-Engine service (n8n API)."""

    def __init__(
        self,
        base_url: str = "http://omni-n8n:5678/api/v1",
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

    def list_workflows(self) -> dict:
        """List all available workflows."""
        logger.info("n8n.list_workflows")
        return self._get("/workflows")

    def get_workflow(self, id: str) -> dict:
        """Get a single workflow by its ID."""
        logger.info("n8n.get_workflow", workflow_id=id)
        return self._get(f"/workflows/{id}")

    def execute_workflow(self, id: str, data: dict | None = None) -> dict:
        """Execute a workflow by its ID, optionally passing input data."""
        logger.info("n8n.execute_workflow", workflow_id=id)
        return self._post(f"/workflows/{id}/execute", data=data or {})

    def list_executions(
        self, workflow_id: str | None = None, status: str | None = None
    ) -> dict:
        """List workflow executions, optionally filtered by workflow ID and status."""
        logger.info(
            "n8n.list_executions", workflow_id=workflow_id, status=status
        )
        params: dict = {}
        if workflow_id is not None:
            params["workflowId"] = workflow_id
        if status is not None:
            params["status"] = status
        return self._get("/executions", **params)

    def get_execution(self, id: str) -> dict:
        """Get details of a single execution by its ID."""
        logger.info("n8n.get_execution", execution_id=id)
        return self._get(f"/executions/{id}")
