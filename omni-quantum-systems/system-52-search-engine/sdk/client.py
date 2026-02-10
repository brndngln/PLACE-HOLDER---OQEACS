from __future__ import annotations
from typing import Any
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class MeilisearchClient:
    def __init__(self, base_url: str, api_key: str):
        self._client = httpx.Client(base_url=base_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params); r.raise_for_status(); return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: Any) -> dict[str, Any]:
        r = self._client.post(path, json=data); r.raise_for_status(); return r.json()

    def search(self, query: str, index: str | None = None, filters: str | None = None, limit: int = 20) -> dict[str, Any]:
        if index:
            return self._post(f"/indexes/{index}/search", {"q": query, "filter": filters, "limit": limit})
        return {idx: self._post(f"/indexes/{idx}/search", {"q": query, "filter": filters, "limit": limit}) for idx in ["knowledge-articles", "code-repositories", "project-issues", "platform-docs", "design-patterns"]}

    def index_document(self, index: str, document: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/indexes/{index}/documents", [document])

    def index_batch(self, index: str, documents: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post(f"/indexes/{index}/documents", documents)

    def delete_document(self, index: str, document_id: str) -> dict[str, Any]:
        return self._post(f"/indexes/{index}/documents/delete-batch", [document_id])

    def get_index_stats(self, index: str) -> dict[str, Any]:
        return self._get(f"/indexes/{index}/stats")
