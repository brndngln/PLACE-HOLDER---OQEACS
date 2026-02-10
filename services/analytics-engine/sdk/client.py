import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class SupersetClient:
    def __init__(
        self,
        base_url: str = "http://omni-superset:8088/api/v1",
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

    def list_dashboards(self) -> list:
        return self._get("/dashboard/").get("result", [])

    def get_dashboard(self, id: int) -> dict:
        return self._get(f"/dashboard/{id}")

    def list_datasets(self) -> list:
        return self._get("/dataset/").get("result", [])

    def run_query(self, dataset_id: int, sql: str) -> dict:
        return self._post("/sqllab/execute/", {"database_id": dataset_id, "sql": sql})

    def export_chart(self, chart_id: int, format: str = "png") -> bytes:
        r = self._client.get(f"/chart/{chart_id}/screenshot/.{format}")
        r.raise_for_status()
        return r.content
