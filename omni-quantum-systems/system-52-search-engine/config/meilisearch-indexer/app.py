from __future__ import annotations

import os
import time
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Query
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential
from fastapi.responses import Response

logger = structlog.get_logger(__name__)

REQ_LAT = Histogram("meili_indexer_request_latency_seconds", "Latency", ["endpoint"])
INDEXED = Counter("meili_indexed_documents_total", "Indexed docs", ["index"])

app = FastAPI(title="Meilisearch Indexer", version="1.0.0")


class DocumentPayload(BaseModel):
    document: dict[str, Any]


class BatchPayload(BaseModel):
    documents: list[dict[str, Any]] = Field(default_factory=list)


class MeiliClient:
    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=os.getenv("MEILI_URL", "http://omni-meilisearch:7700"),
            headers={"Authorization": f"Bearer {os.getenv('MEILI_API_KEY', '')}"},
            timeout=30.0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post(path, json=payload)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def get(self, path: str, **params: Any) -> dict[str, Any]:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()


meili = MeiliClient()


def index_doc(index: str, doc: dict[str, Any]) -> dict[str, Any]:
    data = meili.post(f"/indexes/{index}/documents", [doc])
    INDEXED.labels(index=index).inc()
    return data


@app.post("/index/knowledge")
def index_knowledge(payload: DocumentPayload) -> dict[str, Any]:
    with REQ_LAT.labels("index_knowledge").time():
        return index_doc("knowledge-articles", payload.document)


@app.post("/index/repository")
def index_repository(payload: DocumentPayload) -> dict[str, Any]:
    with REQ_LAT.labels("index_repository").time():
        return index_doc("code-repositories", payload.document)


@app.post("/index/issue")
def index_issue(payload: DocumentPayload) -> dict[str, Any]:
    with REQ_LAT.labels("index_issue").time():
        return index_doc("project-issues", payload.document)


@app.post("/index/wiki")
def index_wiki(payload: DocumentPayload) -> dict[str, Any]:
    with REQ_LAT.labels("index_wiki").time():
        return index_doc("platform-docs", payload.document)


@app.post("/reindex/all")
def reindex_all() -> dict[str, Any]:
    with REQ_LAT.labels("reindex_all").time():
        return {
            "status": "queued",
            "indexes": [
                "knowledge-articles",
                "code-repositories",
                "project-issues",
                "platform-docs",
                "design-patterns",
            ],
            "triggered_at": int(time.time()),
        }


@app.get("/search")
def search(q: str, index: str | None = None, filters: str | None = None, limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    with REQ_LAT.labels("search").time():
        try:
            if index:
                return meili.post(f"/indexes/{index}/search", {"q": q, "filter": filters, "limit": limit})
            results: dict[str, Any] = {}
            for idx in ["knowledge-articles", "code-repositories", "project-issues", "platform-docs", "design-patterns"]:
                results[idx] = meili.post(f"/indexes/{idx}/search", {"q": q, "filter": filters, "limit": limit})
            return {"query": q, "results": results}
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
