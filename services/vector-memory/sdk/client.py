"""Qdrant Manager SDK Client.

System 11 - Vector Memory (Qdrant Collection Management)
Omni Quantum Elite AI Coding System

Async context manager client for interacting with Qdrant vector database
and the snapshot scheduler. Provides both core CRUD operations and
convenience methods that embed text via LiteLLM before searching.

Usage:
    async with QdrantManagerClient() as client:
        collections = await client.list_collections()
        results = await client.get_similar_code("def parse_config", language="python")
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger("qdrant-sdk")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_QDRANT_URL: str = os.getenv("QDRANT_URL", "http://omni-qdrant:6333")
DEFAULT_LITELLM_URL: str = os.getenv("LITELLM_URL", "http://omni-litellm:4000")
DEFAULT_SNAPSHOT_URL: str = os.getenv("SNAPSHOT_SCHEDULER_URL", "http://omni-snapshot-scheduler:6335")
DEFAULT_EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
MAX_RETRIES: int = int(os.getenv("SDK_MAX_RETRIES", "3"))
RETRY_DELAY: float = float(os.getenv("SDK_RETRY_DELAY", "1.0"))
REQUEST_TIMEOUT: float = float(os.getenv("SDK_REQUEST_TIMEOUT", "30.0"))


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------
class CollectionInfo(BaseModel):
    """Summary information about a Qdrant collection."""

    name: str
    status: str = "unknown"
    points_count: int = 0
    vectors_count: int = 0


class CollectionStats(BaseModel):
    """Detailed statistics for a single collection."""

    name: str
    status: str = "unknown"
    points_count: int = 0
    vectors_count: int = 0
    indexed_vectors_count: int = 0
    segments_count: int = 0
    disk_data_size_bytes: int = 0
    ram_data_size_bytes: int = 0
    optimizer_status: str = "unknown"


class ScoredPoint(BaseModel):
    """A single search result with score and payload."""

    id: str | int
    version: int = 0
    score: float = 0.0
    payload: dict[str, Any] = Field(default_factory=dict)
    vector: list[float] | None = None


class SearchResponse(BaseModel):
    """Response from a vector search operation."""

    collection: str
    results: list[ScoredPoint]
    search_time_ms: float = 0.0


class UpsertResponse(BaseModel):
    """Response from an upsert operation."""

    collection: str
    operation_id: int | None = None
    status: str = "acknowledged"


class DeleteResponse(BaseModel):
    """Response from a delete operation."""

    collection: str
    status: str = "acknowledged"


class PointData(BaseModel):
    """A single point to upsert into Qdrant."""

    id: str | int
    vector: list[float]
    payload: dict[str, Any] = Field(default_factory=dict)


class SnapshotResponse(BaseModel):
    """Response from a snapshot operation."""

    collection: str | None = None
    success: bool = False
    snapshot_name: str | None = None
    minio_path: str | None = None
    size_bytes: int = 0
    error: str | None = None


class SnapshotAllResponse(BaseModel):
    """Response from a snapshot-all operation."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    results: list[SnapshotResponse] = Field(default_factory=list)


class FeedbackRecord(BaseModel):
    """Record of stored human feedback."""

    task_id: str
    feedback_type: str
    point_id: str
    collection: str = "human_feedback"
    stored_at: str


# ---------------------------------------------------------------------------
# SDK Client
# ---------------------------------------------------------------------------
class QdrantManagerClient:
    """Async context manager client for Qdrant vector database operations.

    Provides core CRUD operations against Qdrant REST API and convenience
    methods that automatically embed text via LiteLLM before searching.

    Args:
        base_url: Base URL for Qdrant REST API.
        litellm_url: Base URL for LiteLLM embedding proxy.
        snapshot_url: Base URL for the snapshot scheduler service.
        embedding_model: Model identifier for the LiteLLM embedding endpoint.
        max_retries: Maximum number of retries per request.
        retry_delay: Base delay in seconds between retries (exponential backoff).
        timeout: Default request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_QDRANT_URL,
        litellm_url: str = DEFAULT_LITELLM_URL,
        snapshot_url: str = DEFAULT_SNAPSHOT_URL,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY,
        timeout: float = REQUEST_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._litellm_url = litellm_url.rstrip("/")
        self._snapshot_url = snapshot_url.rstrip("/")
        self._embedding_model = embedding_model
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> QdrantManagerClient:
        """Open the underlying httpx async client."""
        self._client = httpx.AsyncClient(timeout=self._timeout)
        log.info(
            "qdrant_sdk_client_opened",
            base_url=self._base_url,
            litellm_url=self._litellm_url,
        )
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any) -> None:
        """Close the underlying httpx async client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            log.info("qdrant_sdk_client_closed")

    @property
    def client(self) -> httpx.AsyncClient:
        """Return the active httpx client, raising if not in context.

        Returns:
            The active httpx.AsyncClient instance.

        Raises:
            RuntimeError: If the client is used outside of an async context manager.
        """
        if self._client is None:
            raise RuntimeError(
                "QdrantManagerClient must be used as an async context manager. "
                "Use: async with QdrantManagerClient() as client: ..."
            )
        return self._client

    # ------------------------------------------------------------------
    # Internal HTTP helper with retry
    # ------------------------------------------------------------------
    async def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | list[Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with automatic retries and exponential backoff.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            url: Full URL to request.
            json_body: Optional JSON payload.
            timeout: Override default timeout for this request.

        Returns:
            httpx.Response on success.

        Raises:
            RuntimeError: After all retries are exhausted.
        """
        import asyncio

        effective_timeout = timeout or self._timeout
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                resp = await self.client.request(
                    method, url, json=json_body, timeout=effective_timeout
                )
                resp.raise_for_status()
                return resp
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_exc = exc
                wait = self._retry_delay * (2 ** (attempt - 1))
                log.warning(
                    "sdk_request_retry",
                    method=method,
                    url=url,
                    attempt=attempt,
                    max_retries=self._max_retries,
                    wait_seconds=wait,
                    error=str(exc),
                )
                await asyncio.sleep(wait)

        raise RuntimeError(
            f"SDK request {method} {url} failed after {self._max_retries} attempts: {last_exc}"
        )

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------
    async def list_collections(self) -> list[CollectionInfo]:
        """List all collections in Qdrant.

        Returns:
            List of CollectionInfo objects.
        """
        url = f"{self._base_url}/collections"
        resp = await self._request("GET", url)
        data = resp.json()
        collections_raw = data.get("result", {}).get("collections", [])
        result: list[CollectionInfo] = []
        for c in collections_raw:
            name = c.get("name", "")
            result.append(CollectionInfo(name=name))
        log.info("list_collections", count=len(result))
        return result

    async def collection_stats(self, name: str) -> CollectionStats:
        """Get detailed statistics for a single collection.

        Args:
            name: Collection name.

        Returns:
            CollectionStats with detailed metrics.
        """
        url = f"{self._base_url}/collections/{name}"
        resp = await self._request("GET", url)
        data = resp.json().get("result", {})
        stats = CollectionStats(
            name=name,
            status=data.get("status", "unknown"),
            points_count=data.get("points_count", 0),
            vectors_count=data.get("vectors_count", 0),
            indexed_vectors_count=data.get("indexed_vectors_count", 0),
            segments_count=data.get("segments_count", 0),
            disk_data_size_bytes=data.get("disk_data_size", 0),
            ram_data_size_bytes=data.get("ram_data_size", 0),
            optimizer_status=str(data.get("optimizer_status", "unknown")),
        )
        log.info("collection_stats", collection=name, points=stats.points_count)
        return stats

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        with_payload: bool = True,
        with_vector: bool = False,
        score_threshold: float | None = None,
    ) -> SearchResponse:
        """Search a collection by vector similarity.

        Args:
            collection: Collection name.
            query_vector: Query embedding vector.
            limit: Maximum number of results.
            filters: Optional Qdrant filter conditions.
            with_payload: Include payload in results.
            with_vector: Include vector in results.
            score_threshold: Minimum score threshold.

        Returns:
            SearchResponse with scored results.
        """
        url = f"{self._base_url}/collections/{collection}/points/search"
        body: dict[str, Any] = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": with_payload,
            "with_vector": with_vector,
        }
        if filters is not None:
            body["filter"] = filters
        if score_threshold is not None:
            body["score_threshold"] = score_threshold

        start = time.monotonic()
        resp = await self._request("POST", url)
        elapsed_ms = (time.monotonic() - start) * 1000

        raw_results = resp.json().get("result", [])
        points: list[ScoredPoint] = []
        for r in raw_results:
            points.append(
                ScoredPoint(
                    id=r.get("id", ""),
                    version=r.get("version", 0),
                    score=r.get("score", 0.0),
                    payload=r.get("payload", {}),
                    vector=r.get("vector") if with_vector else None,
                )
            )

        log.info(
            "search_complete",
            collection=collection,
            results=len(points),
            time_ms=round(elapsed_ms, 2),
        )

        return SearchResponse(
            collection=collection,
            results=points,
            search_time_ms=round(elapsed_ms, 2),
        )

    async def upsert(
        self,
        collection: str,
        points: list[PointData],
    ) -> UpsertResponse:
        """Upsert points into a collection.

        Args:
            collection: Collection name.
            points: List of PointData to upsert.

        Returns:
            UpsertResponse with operation status.
        """
        url = f"{self._base_url}/collections/{collection}/points"
        body: dict[str, Any] = {
            "points": [
                {
                    "id": p.id,
                    "vector": p.vector,
                    "payload": p.payload,
                }
                for p in points
            ]
        }

        resp = await self._request("PUT", url)
        data = resp.json()
        result = data.get("result", {})

        log.info(
            "upsert_complete",
            collection=collection,
            points_count=len(points),
            status=result.get("status", "acknowledged"),
        )

        return UpsertResponse(
            collection=collection,
            operation_id=result.get("operation_id"),
            status=result.get("status", "acknowledged"),
        )

    async def delete(
        self,
        collection: str,
        ids: list[str | int],
    ) -> DeleteResponse:
        """Delete points by ID from a collection.

        Args:
            collection: Collection name.
            ids: List of point IDs to delete.

        Returns:
            DeleteResponse with operation status.
        """
        url = f"{self._base_url}/collections/{collection}/points/delete"
        body: dict[str, Any] = {"points": ids}
        resp = await self._request("POST", url, json_body=body)
        data = resp.json()
        status = data.get("result", {}).get("status", "acknowledged")

        log.info("delete_complete", collection=collection, ids_count=len(ids), status=status)
        return DeleteResponse(collection=collection, status=status)

    async def snapshot(self, collection: str | None = None) -> SnapshotResponse | SnapshotAllResponse:
        """Trigger a snapshot via the snapshot scheduler service.

        Args:
            collection: Optional collection name. If None, snapshots all collections.

        Returns:
            SnapshotResponse for a single collection, or SnapshotAllResponse for all.
        """
        if collection is not None:
            url = f"{self._snapshot_url}/snapshot/{collection}"
            resp = await self._request("POST", url, timeout=600.0)
            data = resp.json()
            log.info("snapshot_triggered", collection=collection)
            return SnapshotResponse(
                collection=data.get("collection", collection),
                success=data.get("success", False),
                snapshot_name=data.get("snapshot_name"),
                minio_path=data.get("minio_path"),
                size_bytes=data.get("size_bytes", 0),
                error=data.get("error"),
            )
        else:
            url = f"{self._snapshot_url}/snapshot/all"
            resp = await self._request("POST", url, timeout=1800.0)
            data = resp.json()
            results: list[SnapshotResponse] = []
            for r in data.get("results", []):
                results.append(
                    SnapshotResponse(
                        collection=r.get("collection"),
                        success=r.get("success", False),
                        snapshot_name=r.get("snapshot_name"),
                        minio_path=r.get("minio_path"),
                        size_bytes=r.get("size_bytes", 0),
                        error=r.get("error"),
                    )
                )
            log.info(
                "snapshot_all_triggered",
                total=data.get("total", 0),
                succeeded=data.get("succeeded", 0),
            )
            return SnapshotAllResponse(
                total=data.get("total", 0),
                succeeded=data.get("succeeded", 0),
                failed=data.get("failed", 0),
                results=results,
            )

    # ------------------------------------------------------------------
    # Helper: embed text via LiteLLM
    # ------------------------------------------------------------------
    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text via LiteLLM.

        Calls the LiteLLM-compatible /v1/embeddings endpoint.

        Args:
            text: Input text to embed.

        Returns:
            Embedding vector as a list of floats.

        Raises:
            RuntimeError: If the embedding request fails.
        """
        url = f"{self._litellm_url}/v1/embeddings"
        body: dict[str, Any] = {
            "model": self._embedding_model,
            "input": text,
        }
        resp = await self._request("POST", url, timeout=30.0)
        data = resp.json()
        embeddings = data.get("data", [])
        if not embeddings:
            raise RuntimeError("LiteLLM returned empty embedding response")
        vector: list[float] = embeddings[0].get("embedding", [])
        if not vector:
            raise RuntimeError("LiteLLM returned empty embedding vector")
        log.debug("text_embedded", model=self._embedding_model, dimensions=len(vector))
        return vector

    # ------------------------------------------------------------------
    # Convenience: get_similar_code
    # ------------------------------------------------------------------
    async def get_similar_code(
        self,
        query_text: str,
        language: str | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> SearchResponse:
        """Find similar code by embedding query text and searching codebase_embeddings.

        Args:
            query_text: Natural language or code snippet to search for.
            language: Optional language filter (e.g., "python", "typescript").
            limit: Maximum number of results.
            score_threshold: Minimum similarity score.

        Returns:
            SearchResponse with matching code embeddings.
        """
        vector = await self.embed_text(query_text)
        filters: dict[str, Any] | None = None
        if language is not None:
            filters = {
                "must": [
                    {
                        "key": "language",
                        "match": {"value": language},
                    }
                ]
            }
        log.info("get_similar_code", language=language, limit=limit)
        return await self.search(
            collection="codebase_embeddings",
            query_vector=vector,
            limit=limit,
            filters=filters,
            score_threshold=score_threshold,
        )

    # ------------------------------------------------------------------
    # Convenience: get_relevant_patterns
    # ------------------------------------------------------------------
    async def get_relevant_patterns(
        self,
        task_description: str,
        limit: int = 5,
        category: str | None = None,
    ) -> SearchResponse:
        """Find relevant design patterns for a given task description.

        Args:
            task_description: Description of the coding task.
            limit: Maximum number of results.
            category: Optional category filter.

        Returns:
            SearchResponse with matching design patterns.
        """
        vector = await self.embed_text(task_description)
        filters: dict[str, Any] | None = None
        if category is not None:
            filters = {
                "must": [
                    {
                        "key": "category",
                        "match": {"value": category},
                    }
                ]
            }
        log.info("get_relevant_patterns", limit=limit, category=category)
        return await self.search(
            collection="design_patterns",
            query_vector=vector,
            limit=limit,
            filters=filters,
        )

    # ------------------------------------------------------------------
    # Convenience: get_anti_patterns
    # ------------------------------------------------------------------
    async def get_anti_patterns(
        self,
        code_snippet: str,
        limit: int = 5,
        language: str | None = None,
        severity: str | None = None,
    ) -> SearchResponse:
        """Find known anti-patterns similar to the given code snippet.

        Args:
            code_snippet: Code to check for anti-pattern matches.
            limit: Maximum number of results.
            language: Optional language filter.
            severity: Optional severity filter.

        Returns:
            SearchResponse with matching anti-patterns.
        """
        vector = await self.embed_text(code_snippet)
        must_conditions: list[dict[str, Any]] = []
        if language is not None:
            must_conditions.append({"key": "language", "match": {"value": language}})
        if severity is not None:
            must_conditions.append({"key": "severity", "match": {"value": severity}})
        filters: dict[str, Any] | None = None
        if must_conditions:
            filters = {"must": must_conditions}
        log.info("get_anti_patterns", limit=limit, language=language, severity=severity)
        return await self.search(
            collection="anti_patterns",
            query_vector=vector,
            limit=limit,
            filters=filters,
        )

    # ------------------------------------------------------------------
    # Convenience: store_feedback
    # ------------------------------------------------------------------
    async def store_feedback(
        self,
        task_id: str,
        feedback_type: str,
        content: str,
        score: float,
        reviewer: str | None = None,
        task_type: str | None = None,
    ) -> FeedbackRecord:
        """Embed and store human feedback in the human_feedback collection.

        Args:
            task_id: Identifier of the task being reviewed.
            feedback_type: One of 'approval', 'rejection', 'revision'.
            content: The feedback text content.
            score: Quality score (0.0 to 1.0).
            reviewer: Optional reviewer identifier.
            task_type: Optional task type classifier.

        Returns:
            FeedbackRecord confirming storage.

        Raises:
            ValueError: If feedback_type is not one of the allowed values.
        """
        allowed_types = {"approval", "rejection", "revision"}
        if feedback_type not in allowed_types:
            raise ValueError(
                f"feedback_type must be one of {allowed_types}, got '{feedback_type}'"
            )

        vector = await self.embed_text(content)
        point_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        payload: dict[str, Any] = {
            "task_id": task_id,
            "feedback_type": feedback_type,
            "content": content,
            "quality_score": score,
            "timestamp": now_iso,
        }
        if reviewer is not None:
            payload["reviewer"] = reviewer
        if task_type is not None:
            payload["task_type"] = task_type

        point = PointData(id=point_id, vector=vector, payload=payload)
        await self.upsert(collection="human_feedback", points=[point])

        log.info(
            "feedback_stored",
            task_id=task_id,
            feedback_type=feedback_type,
            point_id=point_id,
            score=score,
        )

        return FeedbackRecord(
            task_id=task_id,
            feedback_type=feedback_type,
            point_id=point_id,
            collection="human_feedback",
            stored_at=now_iso,
        )
