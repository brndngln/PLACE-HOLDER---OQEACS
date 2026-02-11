import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class ContextCompilerClient:
    def __init__(self, base_url: str = "http://omni-context-compiler:8325", api_token: str = ""):
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

    def compile_context(
        self, task_description: str, repo_url: str | None = None, files: list[str] | None = None
    ) -> dict:
        """Compile context for a task from the given description, repo, and files."""
        payload = {"task_description": task_description}
        if repo_url is not None:
            payload["repo_url"] = repo_url
        if files is not None:
            payload["files"] = files
        logger.info("compiling_context", has_repo=repo_url is not None, file_count=len(files) if files else 0)
        return self._post("/api/v1/compile", payload)

    def get_context(self, id: str) -> dict:
        """Get a previously compiled context by its ID."""
        logger.info("getting_context", context_id=id)
        return self._get(f"/api/v1/contexts/{id}")

    def list_compilations(self) -> dict:
        """List all context compilations."""
        logger.info("listing_compilations")
        return self._get("/api/v1/compilations")
