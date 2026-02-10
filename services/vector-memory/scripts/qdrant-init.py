#!/usr/bin/env python3
"""Qdrant Collection Initialization Script.

System 11 - Vector Memory (Qdrant Collection Management)
Omni Quantum Elite AI Coding System

Waits for Qdrant health at omni-qdrant:6333, creates 7 collections with
HNSW tuning, payload indexes, quantization, verifies each with a test
upsert+search+delete cycle, then registers with the Orchestrator.

Usage:
    python qdrant-init.py
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
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

log = structlog.get_logger("qdrant-init")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://omni-qdrant:6333")
ORCHESTRATOR_URL: str = os.getenv("ORCHESTRATOR_URL", "http://omni-orchestrator:9500")
VECTOR_SIZE: int = 768
DISTANCE: str = "Cosine"
HEALTH_TIMEOUT: int = int(os.getenv("QDRANT_HEALTH_TIMEOUT", "300"))
HEALTH_INTERVAL: int = int(os.getenv("QDRANT_HEALTH_INTERVAL", "5"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "5"))
RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "2.0"))


# ---------------------------------------------------------------------------
# Pydantic models for payload index specifications
# ---------------------------------------------------------------------------
class PayloadIndex(BaseModel):
    """Describes a single payload field index to create."""

    field_name: str
    field_schema: str  # keyword | integer | float | text | datetime


class CollectionSpec(BaseModel):
    """Full specification for one Qdrant collection."""

    name: str
    hnsw_m: int = 16
    hnsw_ef: int = 128
    payload_indexes: list[PayloadIndex] = Field(default_factory=list)
    quantization: dict[str, Any] | None = None
    on_disk_payload: bool = False
    description: str = ""


# ---------------------------------------------------------------------------
# Collection definitions
# ---------------------------------------------------------------------------
COLLECTIONS: list[CollectionSpec] = [
    CollectionSpec(
        name="codebase_embeddings",
        hnsw_m=16,
        hnsw_ef=256,
        on_disk_payload=True,
        quantization={
            "scalar": {
                "type": "int8",
                "quantile": 0.99,
                "always_ram": True,
            }
        },
        description="Primary codebase embedding store with scalar int8 quantization and on-disk payload",
        payload_indexes=[
            PayloadIndex(field_name="language", field_schema="keyword"),
            PayloadIndex(field_name="repository", field_schema="keyword"),
            PayloadIndex(field_name="file_path", field_schema="keyword"),
            PayloadIndex(field_name="function_name", field_schema="text"),
            PayloadIndex(field_name="complexity", field_schema="integer"),
            PayloadIndex(field_name="quality_score", field_schema="float"),
            PayloadIndex(field_name="ingested_at", field_schema="datetime"),
        ],
    ),
    CollectionSpec(
        name="design_patterns",
        hnsw_m=16,
        hnsw_ef=128,
        description="Design pattern repository (~500-2000 entries)",
        payload_indexes=[
            PayloadIndex(field_name="category", field_schema="keyword"),
            PayloadIndex(field_name="pattern_name", field_schema="keyword"),
            PayloadIndex(field_name="languages", field_schema="keyword"),
            PayloadIndex(field_name="complexity", field_schema="integer"),
            PayloadIndex(field_name="source_codebase", field_schema="keyword"),
        ],
    ),
    CollectionSpec(
        name="anti_patterns",
        hnsw_m=16,
        hnsw_ef=128,
        description="Anti-pattern detection store with 1-year TTL review cycle",
        payload_indexes=[
            PayloadIndex(field_name="error_type", field_schema="keyword"),
            PayloadIndex(field_name="language", field_schema="keyword"),
            PayloadIndex(field_name="pipeline_stage", field_schema="keyword"),
            PayloadIndex(field_name="rejection_reason", field_schema="text"),
            PayloadIndex(field_name="severity", field_schema="keyword"),
            PayloadIndex(field_name="detected_at", field_schema="datetime"),
        ],
    ),
    CollectionSpec(
        name="human_feedback",
        hnsw_m=16,
        hnsw_ef=128,
        description="Human feedback store - never auto-delete",
        payload_indexes=[
            PayloadIndex(field_name="feedback_type", field_schema="keyword"),
            PayloadIndex(field_name="reviewer", field_schema="keyword"),
            PayloadIndex(field_name="task_type", field_schema="keyword"),
            PayloadIndex(field_name="quality_score", field_schema="float"),
            PayloadIndex(field_name="timestamp", field_schema="datetime"),
        ],
    ),
    CollectionSpec(
        name="academic_papers",
        hnsw_m=16,
        hnsw_ef=128,
        description="Academic paper embeddings - sections stored separately",
        payload_indexes=[
            PayloadIndex(field_name="domain", field_schema="keyword"),
            PayloadIndex(field_name="title", field_schema="text"),
            PayloadIndex(field_name="authors", field_schema="keyword"),
            PayloadIndex(field_name="year", field_schema="integer"),
            PayloadIndex(field_name="venue", field_schema="keyword"),
            PayloadIndex(field_name="citation_count", field_schema="integer"),
        ],
    ),
    CollectionSpec(
        name="elite_codebases",
        hnsw_m=16,
        hnsw_ef=256,
        description="Crown jewel collection - elite codebase embeddings",
        payload_indexes=[
            PayloadIndex(field_name="project", field_schema="keyword"),
            PayloadIndex(field_name="language", field_schema="keyword"),
            PayloadIndex(field_name="component", field_schema="keyword"),
            PayloadIndex(field_name="pattern_tags", field_schema="keyword"),
            PayloadIndex(field_name="complexity", field_schema="integer"),
        ],
    ),
    CollectionSpec(
        name="project_context",
        hnsw_m=16,
        hnsw_ef=128,
        description="Project context store - isolated per project",
        payload_indexes=[
            PayloadIndex(field_name="project_id", field_schema="keyword"),
            PayloadIndex(field_name="context_type", field_schema="keyword"),
            PayloadIndex(field_name="timestamp", field_schema="datetime"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# HTTP helpers with retry
# ---------------------------------------------------------------------------
def _request(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    json_body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> httpx.Response:
    """Execute an HTTP request with automatic retries and exponential backoff.

    Args:
        client: httpx client instance.
        method: HTTP method (GET, PUT, POST, DELETE, PATCH).
        url: Full URL to request.
        json_body: Optional JSON body for the request.
        timeout: Request timeout in seconds.

    Returns:
        httpx.Response on success.

    Raises:
        RuntimeError: After all retries are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.request(
                method,
                url,
                json=json_body,
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            last_exc = exc
            wait = RETRY_DELAY * (2 ** (attempt - 1))
            log.warning(
                "request_failed",
                method=method,
                url=url,
                attempt=attempt,
                max_retries=MAX_RETRIES,
                wait_seconds=wait,
                error=str(exc),
            )
            time.sleep(wait)
    raise RuntimeError(
        f"Request {method} {url} failed after {MAX_RETRIES} attempts: {last_exc}"
    )


# ---------------------------------------------------------------------------
# Health wait
# ---------------------------------------------------------------------------
def wait_for_qdrant(client: httpx.Client) -> None:
    """Block until Qdrant is healthy or timeout is reached.

    Args:
        client: httpx client instance.

    Raises:
        SystemExit: If Qdrant does not become healthy within HEALTH_TIMEOUT.
    """
    log.info("waiting_for_qdrant", url=QDRANT_URL, timeout=HEALTH_TIMEOUT)
    deadline = time.monotonic() + HEALTH_TIMEOUT
    while time.monotonic() < deadline:
        try:
            resp = client.get(f"{QDRANT_URL}/healthz", timeout=5.0)
            if resp.status_code == 200:
                log.info("qdrant_healthy")
                return
        except (httpx.TransportError, httpx.HTTPStatusError):
            pass
        log.debug("qdrant_not_ready_yet", remaining=int(deadline - time.monotonic()))
        time.sleep(HEALTH_INTERVAL)
    log.error("qdrant_health_timeout", timeout=HEALTH_TIMEOUT)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Collection creation
# ---------------------------------------------------------------------------
def _build_collection_body(spec: CollectionSpec) -> dict[str, Any]:
    """Build the JSON body for the Qdrant PUT /collections/{name} endpoint.

    Args:
        spec: Collection specification.

    Returns:
        Dictionary suitable for JSON serialisation.
    """
    body: dict[str, Any] = {
        "vectors": {
            "size": VECTOR_SIZE,
            "distance": DISTANCE,
            "on_disk": False,
        },
        "hnsw_config": {
            "m": spec.hnsw_m,
            "ef_construct": spec.hnsw_ef,
        },
        "optimizers_config": {
            "indexing_threshold": 20000,
            "memmap_threshold": 50000,
        },
        "on_disk_payload": spec.on_disk_payload,
    }
    if spec.quantization is not None:
        body["quantization_config"] = spec.quantization
    return body


def create_collection(client: httpx.Client, spec: CollectionSpec) -> None:
    """Create a single Qdrant collection with the given specification.

    If the collection already exists the step is skipped.

    Args:
        client: httpx client instance.
        spec: Collection specification.
    """
    url = f"{QDRANT_URL}/collections/{spec.name}"
    # Check existence
    try:
        resp = client.get(url, timeout=10.0)
        if resp.status_code == 200:
            log.info("collection_exists", collection=spec.name)
            return
    except (httpx.TransportError, httpx.HTTPStatusError):
        pass

    body = _build_collection_body(spec)
    log.info("creating_collection", collection=spec.name, hnsw_m=spec.hnsw_m, hnsw_ef=spec.hnsw_ef)
    _request(client, "PUT", url, json_body=body)
    log.info("collection_created", collection=spec.name)


def create_payload_indexes(client: httpx.Client, spec: CollectionSpec) -> None:
    """Create payload field indexes for a collection.

    Args:
        client: httpx client instance.
        spec: Collection specification with payload index definitions.
    """
    url = f"{QDRANT_URL}/collections/{spec.name}/index"
    for idx in spec.payload_indexes:
        payload: dict[str, Any] = {
            "field_name": idx.field_name,
            "field_schema": idx.field_schema,
        }
        log.info(
            "creating_payload_index",
            collection=spec.name,
            field=idx.field_name,
            schema=idx.field_schema,
        )
        try:
            _request(client, "PUT", url, json_body=payload)
        except RuntimeError:
            log.warning(
                "payload_index_may_exist",
                collection=spec.name,
                field=idx.field_name,
            )


# ---------------------------------------------------------------------------
# Verification: upsert -> search -> delete
# ---------------------------------------------------------------------------
def verify_collection(client: httpx.Client, collection_name: str) -> bool:
    """Verify a collection by performing a test upsert, search, and delete.

    Args:
        client: httpx client instance.
        collection_name: Name of the collection to verify.

    Returns:
        True if verification passes, False otherwise.
    """
    test_id = str(uuid.uuid4())
    test_vector = [0.01] * VECTOR_SIZE
    test_payload = {"_verification": True, "_test_id": test_id}

    log.info("verifying_collection", collection=collection_name, test_id=test_id)

    # 1. Upsert test point
    upsert_url = f"{QDRANT_URL}/collections/{collection_name}/points"
    upsert_body: dict[str, Any] = {
        "points": [
            {
                "id": test_id,
                "vector": test_vector,
                "payload": test_payload,
            }
        ]
    }
    try:
        _request(client, "PUT", upsert_url, json_body=upsert_body)
    except RuntimeError as exc:
        log.error("verify_upsert_failed", collection=collection_name, error=str(exc))
        return False

    # Allow Qdrant a moment to index
    time.sleep(0.5)

    # 2. Search for the test point
    search_url = f"{QDRANT_URL}/collections/{collection_name}/points/search"
    search_body: dict[str, Any] = {
        "vector": test_vector,
        "limit": 1,
        "with_payload": True,
    }
    try:
        resp = _request(client, "POST", search_url, json_body=search_body)
        results = resp.json().get("result", [])
        if not results:
            log.error("verify_search_empty", collection=collection_name)
            return False
        found_id = str(results[0].get("id", ""))
        if found_id != test_id:
            log.warning(
                "verify_search_id_mismatch",
                collection=collection_name,
                expected=test_id,
                found=found_id,
            )
    except RuntimeError as exc:
        log.error("verify_search_failed", collection=collection_name, error=str(exc))
        return False

    # 3. Delete test point
    delete_url = f"{QDRANT_URL}/collections/{collection_name}/points/delete"
    delete_body: dict[str, Any] = {"points": [test_id]}
    try:
        _request(client, "POST", delete_url, json_body=delete_body)
    except RuntimeError as exc:
        log.error("verify_delete_failed", collection=collection_name, error=str(exc))
        return False

    log.info("collection_verified", collection=collection_name)
    return True


# ---------------------------------------------------------------------------
# Orchestrator registration
# ---------------------------------------------------------------------------
def register_with_orchestrator(client: httpx.Client, collections: list[str]) -> None:
    """Register the Vector Memory system and its collections with the Orchestrator.

    Args:
        client: httpx client instance.
        collections: List of successfully created collection names.
    """
    registration_payload: dict[str, Any] = {
        "service": "vector-memory",
        "component": "qdrant",
        "version": "1.0.0",
        "endpoints": {
            "rest": f"{QDRANT_URL}",
            "grpc": "omni-qdrant:6334",
            "snapshot_scheduler": "http://omni-snapshot-scheduler:6335",
        },
        "collections": collections,
        "capabilities": [
            "vector_search",
            "payload_filtering",
            "snapshot_management",
            "scalar_quantization",
        ],
        "status": "healthy",
    }
    register_url = f"{ORCHESTRATOR_URL}/api/v1/services/register"
    log.info("registering_with_orchestrator", url=register_url, collections=collections)
    try:
        _request(client, "POST", register_url, json_body=registration_payload)
        log.info("orchestrator_registration_success")
    except RuntimeError as exc:
        log.warning(
            "orchestrator_registration_failed",
            error=str(exc),
            note="System will continue without orchestrator registration",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Entry point: wait for Qdrant, create collections, verify, register."""
    log.info(
        "qdrant_init_starting",
        qdrant_url=QDRANT_URL,
        orchestrator_url=ORCHESTRATOR_URL,
        vector_size=VECTOR_SIZE,
        distance=DISTANCE,
        num_collections=len(COLLECTIONS),
    )

    with httpx.Client() as client:
        # 1. Wait for Qdrant to be healthy
        wait_for_qdrant(client)

        # 2. Create collections and payload indexes
        created: list[str] = []
        failed: list[str] = []
        for spec in COLLECTIONS:
            try:
                create_collection(client, spec)
                create_payload_indexes(client, spec)
                created.append(spec.name)
            except RuntimeError as exc:
                log.error(
                    "collection_creation_failed",
                    collection=spec.name,
                    error=str(exc),
                )
                failed.append(spec.name)

        # 3. Verify every created collection
        verified: list[str] = []
        for name in created:
            if verify_collection(client, name):
                verified.append(name)
            else:
                failed.append(name)

        # 4. Register with Orchestrator
        if verified:
            register_with_orchestrator(client, verified)

        # 5. Summary
        log.info(
            "qdrant_init_complete",
            total=len(COLLECTIONS),
            verified=len(verified),
            failed=len(failed),
            verified_collections=verified,
            failed_collections=failed,
        )

        if failed:
            log.error("some_collections_failed", collections=failed)
            sys.exit(1)

    log.info("qdrant_init_finished_successfully")


if __name__ == "__main__":
    main()
