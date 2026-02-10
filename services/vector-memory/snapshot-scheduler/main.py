#!/usr/bin/env python3
"""Qdrant Snapshot Scheduler Service.

System 11 - Vector Memory (Qdrant Collection Management)
Omni Quantum Elite AI Coding System

FastAPI service on port 6335 that manages Qdrant collection snapshots with
automatic daily scheduling (2 AM), MinIO archival, checksum verification,
and 30-day retention policy.

Endpoints:
    POST /snapshot/all            - Snapshot all collections to MinIO
    POST /snapshot/{collection}   - Snapshot a specific collection
    GET  /snapshot/status          - Last snapshot time + size per collection
    GET  /collections/stats        - Entry/vector count, disk usage per collection
    GET  /health                   - Health check
    GET  /metrics                  - Prometheus metrics

Usage:
    uvicorn main:app --host 0.0.0.0 --port 6335
"""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Response
from minio import Minio
from minio.error import S3Error
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
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

log = structlog.get_logger("snapshot-scheduler")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://omni-qdrant:6333")
MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "omni-minio:9000")
MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "omni-backups-qdrant")
MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "2.0"))
RETENTION_DAYS: int = int(os.getenv("RETENTION_DAYS", "30"))
SNAPSHOT_CRON_HOUR: int = int(os.getenv("SNAPSHOT_CRON_HOUR", "2"))
SNAPSHOT_CRON_MINUTE: int = int(os.getenv("SNAPSHOT_CRON_MINUTE", "0"))

KNOWN_COLLECTIONS: list[str] = [
    "codebase_embeddings",
    "design_patterns",
    "anti_patterns",
    "human_feedback",
    "academic_papers",
    "elite_codebases",
    "project_context",
]

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
registry = CollectorRegistry()

metric_snapshot_last_success = Gauge(
    "qdrant_snapshot_last_success",
    "Unix timestamp of last successful snapshot",
    ["collection"],
    registry=registry,
)
metric_snapshot_size_bytes = Gauge(
    "qdrant_snapshot_size_bytes",
    "Size in bytes of last successful snapshot",
    ["collection"],
    registry=registry,
)
metric_collection_vectors_total = Gauge(
    "qdrant_collection_vectors_total",
    "Total number of vectors in collection",
    ["collection"],
    registry=registry,
)

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------
class SnapshotResult(BaseModel):
    """Result of a single collection snapshot operation."""

    collection: str
    success: bool
    snapshot_name: str | None = None
    minio_path: str | None = None
    size_bytes: int = 0
    checksum_sha256: str | None = None
    error: str | None = None
    duration_seconds: float = 0.0


class SnapshotAllResponse(BaseModel):
    """Response for the snapshot-all endpoint."""

    started_at: str
    completed_at: str
    total: int
    succeeded: int
    failed: int
    results: list[SnapshotResult]


class CollectionSnapshotStatus(BaseModel):
    """Snapshot status for a single collection."""

    collection: str
    last_snapshot_time: str | None = None
    last_snapshot_size_bytes: int = 0
    minio_path: str | None = None


class SnapshotStatusResponse(BaseModel):
    """Response for snapshot status endpoint."""

    collections: list[CollectionSnapshotStatus]


class CollectionStatEntry(BaseModel):
    """Statistics for a single collection."""

    collection: str
    points_count: int = 0
    vectors_count: int = 0
    indexed_vectors_count: int = 0
    segments_count: int = 0
    disk_data_size_bytes: int = 0
    ram_data_size_bytes: int = 0
    status: str = "unknown"


class CollectionStatsResponse(BaseModel):
    """Response for collection stats endpoint."""

    collections: list[CollectionStatEntry]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    qdrant_reachable: bool
    minio_reachable: bool
    scheduler_running: bool
    timestamp: str


# ---------------------------------------------------------------------------
# In-memory snapshot status tracker
# ---------------------------------------------------------------------------
_snapshot_status: dict[str, CollectionSnapshotStatus] = {}


# ---------------------------------------------------------------------------
# MinIO client helper
# ---------------------------------------------------------------------------
def get_minio_client() -> Minio:
    """Create and return a configured MinIO client.

    Returns:
        Minio client instance.
    """
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def ensure_minio_bucket(mc: Minio) -> None:
    """Ensure the snapshot bucket exists in MinIO.

    Args:
        mc: MinIO client instance.
    """
    if not mc.bucket_exists(MINIO_BUCKET):
        mc.make_bucket(MINIO_BUCKET)
        log.info("minio_bucket_created", bucket=MINIO_BUCKET)


# ---------------------------------------------------------------------------
# HTTP helpers with retry
# ---------------------------------------------------------------------------
async def _async_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    json_body: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> httpx.Response:
    """Execute an async HTTP request with retries and exponential backoff.

    Args:
        client: httpx async client.
        method: HTTP method.
        url: Full URL.
        json_body: Optional JSON body.
        timeout: Per-request timeout in seconds.

    Returns:
        httpx.Response on success.

    Raises:
        RuntimeError: After all retries are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.request(method, url, json=json_body, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            last_exc = exc
            wait = RETRY_DELAY * (2 ** (attempt - 1))
            log.warning(
                "async_request_failed",
                method=method,
                url=url,
                attempt=attempt,
                max_retries=MAX_RETRIES,
                wait_seconds=wait,
                error=str(exc),
            )
            import asyncio
            await asyncio.sleep(wait)
    raise RuntimeError(
        f"Request {method} {url} failed after {MAX_RETRIES} attempts: {last_exc}"
    )


# ---------------------------------------------------------------------------
# Core snapshot logic
# ---------------------------------------------------------------------------
async def snapshot_collection(collection: str) -> SnapshotResult:
    """Perform a full snapshot cycle for a single collection.

    Steps:
        1. Trigger snapshot via Qdrant REST API
        2. Download the snapshot file
        3. Compute SHA-256 checksum
        4. Upload to MinIO at {collection}/{date}/snapshot.tar
        5. Verify upload checksum
        6. Cleanup local temporary file
        7. Purge snapshots older than RETENTION_DAYS from MinIO

    Args:
        collection: Name of the Qdrant collection.

    Returns:
        SnapshotResult with details of the operation.
    """
    start = time.monotonic()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    minio_path = f"{collection}/{date_str}/snapshot.tar"

    log.info("snapshot_starting", collection=collection, date=date_str)

    async with httpx.AsyncClient() as client:
        # --- Step 1: Create snapshot in Qdrant ---
        try:
            create_url = f"{QDRANT_URL}/collections/{collection}/snapshots"
            resp = await _async_request(client, "POST", create_url, timeout=300.0)
            snapshot_info = resp.json().get("result", {})
            snapshot_name = snapshot_info.get("name", "")
            if not snapshot_name:
                return SnapshotResult(
                    collection=collection,
                    success=False,
                    error="Qdrant returned empty snapshot name",
                    duration_seconds=time.monotonic() - start,
                )
            log.info("snapshot_created_in_qdrant", collection=collection, snapshot_name=snapshot_name)
        except RuntimeError as exc:
            return SnapshotResult(
                collection=collection,
                success=False,
                error=f"Failed to create snapshot: {exc}",
                duration_seconds=time.monotonic() - start,
            )

        # --- Step 2: Download snapshot ---
        download_url = f"{QDRANT_URL}/collections/{collection}/snapshots/{snapshot_name}"
        tmp_dir = tempfile.mkdtemp(prefix="qdrant_snapshot_")
        local_path = Path(tmp_dir) / "snapshot.tar"

        try:
            async with client.stream("GET", download_url, timeout=600.0) as stream:
                stream.raise_for_status()
                sha256 = hashlib.sha256()
                total_size = 0
                with open(local_path, "wb") as f:
                    async for chunk in stream.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
                        sha256.update(chunk)
                        total_size += len(chunk)
            checksum = sha256.hexdigest()
            log.info(
                "snapshot_downloaded",
                collection=collection,
                size_bytes=total_size,
                checksum=checksum,
            )
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            _cleanup_local(local_path, tmp_dir)
            return SnapshotResult(
                collection=collection,
                success=False,
                snapshot_name=snapshot_name,
                error=f"Failed to download snapshot: {exc}",
                duration_seconds=time.monotonic() - start,
            )

        # --- Step 3 & 4: Upload to MinIO ---
        try:
            mc = get_minio_client()
            ensure_minio_bucket(mc)
            mc.fput_object(
                MINIO_BUCKET,
                minio_path,
                str(local_path),
                content_type="application/x-tar",
                metadata={"x-amz-meta-sha256": checksum},
            )
            log.info("snapshot_uploaded_to_minio", collection=collection, path=minio_path)
        except S3Error as exc:
            _cleanup_local(local_path, tmp_dir)
            return SnapshotResult(
                collection=collection,
                success=False,
                snapshot_name=snapshot_name,
                error=f"MinIO upload failed: {exc}",
                duration_seconds=time.monotonic() - start,
            )

        # --- Step 5: Verify upload ---
        try:
            stat = mc.stat_object(MINIO_BUCKET, minio_path)
            uploaded_meta = stat.metadata or {}
            remote_checksum = uploaded_meta.get("x-amz-meta-sha256", "")
            if remote_checksum and remote_checksum != checksum:
                log.error(
                    "snapshot_checksum_mismatch",
                    collection=collection,
                    local=checksum,
                    remote=remote_checksum,
                )
                _cleanup_local(local_path, tmp_dir)
                return SnapshotResult(
                    collection=collection,
                    success=False,
                    snapshot_name=snapshot_name,
                    minio_path=minio_path,
                    error="Checksum mismatch after upload",
                    duration_seconds=time.monotonic() - start,
                )
            log.info("snapshot_checksum_verified", collection=collection)
        except S3Error as exc:
            log.warning("snapshot_verify_failed", collection=collection, error=str(exc))

        # --- Step 6: Cleanup local ---
        _cleanup_local(local_path, tmp_dir)

        # --- Step 7: Delete Qdrant-side snapshot ---
        try:
            delete_snap_url = f"{QDRANT_URL}/collections/{collection}/snapshots/{snapshot_name}"
            await _async_request(client, "DELETE", delete_snap_url, timeout=30.0)
            log.info("qdrant_snapshot_deleted", collection=collection, snapshot_name=snapshot_name)
        except RuntimeError:
            log.warning("qdrant_snapshot_delete_failed", collection=collection, snapshot_name=snapshot_name)

        # --- Step 8: Purge old snapshots from MinIO ---
        try:
            _purge_old_snapshots(mc, collection)
        except Exception as exc:
            log.warning("purge_old_snapshots_failed", collection=collection, error=str(exc))

    duration = time.monotonic() - start

    # Update in-memory status
    now_iso = datetime.now(timezone.utc).isoformat()
    _snapshot_status[collection] = CollectionSnapshotStatus(
        collection=collection,
        last_snapshot_time=now_iso,
        last_snapshot_size_bytes=total_size,
        minio_path=f"{MINIO_BUCKET}/{minio_path}",
    )

    # Update Prometheus metrics
    metric_snapshot_last_success.labels(collection=collection).set(time.time())
    metric_snapshot_size_bytes.labels(collection=collection).set(total_size)

    log.info(
        "snapshot_complete",
        collection=collection,
        size_bytes=total_size,
        duration_seconds=round(duration, 2),
    )

    return SnapshotResult(
        collection=collection,
        success=True,
        snapshot_name=snapshot_name,
        minio_path=f"{MINIO_BUCKET}/{minio_path}",
        size_bytes=total_size,
        checksum_sha256=checksum,
        duration_seconds=round(duration, 2),
    )


def _cleanup_local(local_path: Path, tmp_dir: str) -> None:
    """Remove the local snapshot file and temp directory.

    Args:
        local_path: Path to the local snapshot file.
        tmp_dir: Path to the temporary directory.
    """
    try:
        if local_path.exists():
            local_path.unlink()
        Path(tmp_dir).rmdir()
    except OSError as exc:
        log.warning("cleanup_failed", path=str(local_path), error=str(exc))


def _purge_old_snapshots(mc: Minio, collection: str) -> None:
    """Delete MinIO snapshot objects older than RETENTION_DAYS.

    Args:
        mc: MinIO client.
        collection: Collection name prefix in the bucket.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    prefix = f"{collection}/"
    objects = mc.list_objects(MINIO_BUCKET, prefix=prefix, recursive=True)
    deleted_count = 0
    for obj in objects:
        if obj.last_modified and obj.last_modified < cutoff:
            mc.remove_object(MINIO_BUCKET, obj.object_name)
            deleted_count += 1
            log.info(
                "old_snapshot_deleted",
                collection=collection,
                object_name=obj.object_name,
                last_modified=obj.last_modified.isoformat(),
            )
    if deleted_count > 0:
        log.info("purge_complete", collection=collection, deleted=deleted_count)


# ---------------------------------------------------------------------------
# Scheduled job
# ---------------------------------------------------------------------------
async def scheduled_snapshot_all() -> None:
    """Run daily scheduled snapshot for all known collections."""
    log.info("scheduled_snapshot_all_starting")
    for collection in KNOWN_COLLECTIONS:
        try:
            await snapshot_collection(collection)
        except Exception as exc:
            log.error("scheduled_snapshot_failed", collection=collection, error=str(exc))
    log.info("scheduled_snapshot_all_complete")


# ---------------------------------------------------------------------------
# Collection stats helper
# ---------------------------------------------------------------------------
async def fetch_collection_stats() -> list[CollectionStatEntry]:
    """Fetch statistics for all known collections from Qdrant.

    Returns:
        List of CollectionStatEntry with current stats.
    """
    entries: list[CollectionStatEntry] = []
    async with httpx.AsyncClient() as client:
        for name in KNOWN_COLLECTIONS:
            url = f"{QDRANT_URL}/collections/{name}"
            try:
                resp = await _async_request(client, "GET", url, timeout=10.0)
                data = resp.json().get("result", {})
                points_count = data.get("points_count", 0)
                vectors_count = data.get("vectors_count", 0)
                indexed_vectors_count = data.get("indexed_vectors_count", 0)
                segments_count = data.get("segments_count", 0)
                disk_size = data.get("disk_data_size", 0)
                ram_size = data.get("ram_data_size", 0)
                status = data.get("status", "unknown")

                # Update Prometheus gauge
                metric_collection_vectors_total.labels(collection=name).set(vectors_count)

                entries.append(
                    CollectionStatEntry(
                        collection=name,
                        points_count=points_count,
                        vectors_count=vectors_count,
                        indexed_vectors_count=indexed_vectors_count,
                        segments_count=segments_count,
                        disk_data_size_bytes=disk_size,
                        ram_data_size_bytes=ram_size,
                        status=status,
                    )
                )
            except RuntimeError as exc:
                log.warning("collection_stats_failed", collection=name, error=str(exc))
                entries.append(CollectionStatEntry(collection=name, status="unreachable"))
    return entries


# ---------------------------------------------------------------------------
# APScheduler setup
# ---------------------------------------------------------------------------
scheduler = AsyncIOScheduler()


# ---------------------------------------------------------------------------
# FastAPI app lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: start/stop scheduler."""
    scheduler.add_job(
        scheduled_snapshot_all,
        CronTrigger(hour=SNAPSHOT_CRON_HOUR, minute=SNAPSHOT_CRON_MINUTE),
        id="daily_snapshot_all",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    log.info(
        "scheduler_started",
        cron=f"{SNAPSHOT_CRON_MINUTE} {SNAPSHOT_CRON_HOUR} * * *",
    )
    yield
    scheduler.shutdown(wait=False)
    log.info("scheduler_stopped")


app = FastAPI(
    title="Qdrant Snapshot Scheduler",
    description="System 11 - Vector Memory snapshot management for Omni Quantum Elite AI Coding System",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/snapshot/all", response_model=SnapshotAllResponse)
async def snapshot_all_collections() -> SnapshotAllResponse:
    """Create snapshots for all known collections and upload to MinIO.

    Returns:
        SnapshotAllResponse with per-collection results.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    results: list[SnapshotResult] = []

    for collection in KNOWN_COLLECTIONS:
        try:
            result = await snapshot_collection(collection)
            results.append(result)
        except Exception as exc:
            log.error("snapshot_all_error", collection=collection, error=str(exc))
            results.append(
                SnapshotResult(
                    collection=collection,
                    success=False,
                    error=str(exc),
                )
            )

    completed_at = datetime.now(timezone.utc).isoformat()
    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    log.info(
        "snapshot_all_complete",
        total=len(results),
        succeeded=succeeded,
        failed=failed,
    )

    return SnapshotAllResponse(
        started_at=started_at,
        completed_at=completed_at,
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        results=results,
    )


@app.post("/snapshot/{collection}", response_model=SnapshotResult)
async def snapshot_single_collection(collection: str) -> SnapshotResult:
    """Create a snapshot for a specific collection and upload to MinIO.

    Args:
        collection: Name of the Qdrant collection.

    Returns:
        SnapshotResult with operation details.

    Raises:
        HTTPException: If the collection is not in the known list.
    """
    if collection not in KNOWN_COLLECTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown collection '{collection}'. Known: {KNOWN_COLLECTIONS}",
        )
    try:
        return await snapshot_collection(collection)
    except Exception as exc:
        log.error("snapshot_single_error", collection=collection, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/snapshot/status", response_model=SnapshotStatusResponse)
async def get_snapshot_status() -> SnapshotStatusResponse:
    """Return last snapshot time and size per collection.

    Returns:
        SnapshotStatusResponse with per-collection status.
    """
    statuses: list[CollectionSnapshotStatus] = []
    for name in KNOWN_COLLECTIONS:
        if name in _snapshot_status:
            statuses.append(_snapshot_status[name])
        else:
            statuses.append(CollectionSnapshotStatus(collection=name))
    return SnapshotStatusResponse(collections=statuses)


@app.get("/collections/stats", response_model=CollectionStatsResponse)
async def get_collection_stats() -> CollectionStatsResponse:
    """Return entry count, vector count, and disk usage per collection.

    Returns:
        CollectionStatsResponse with per-collection statistics.
    """
    entries = await fetch_collection_stats()
    return CollectionStatsResponse(collections=entries)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint verifying Qdrant, MinIO, and scheduler status.

    Returns:
        HealthResponse with component reachability status.
    """
    qdrant_ok = False
    minio_ok = False
    scheduler_ok = scheduler.running

    # Check Qdrant
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{QDRANT_URL}/healthz", timeout=5.0)
            qdrant_ok = resp.status_code == 200
        except (httpx.TransportError, httpx.HTTPStatusError):
            pass

    # Check MinIO
    try:
        mc = get_minio_client()
        mc.bucket_exists(MINIO_BUCKET)
        minio_ok = True
    except Exception:
        pass

    overall = "healthy" if (qdrant_ok and minio_ok and scheduler_ok) else "degraded"

    return HealthResponse(
        status=overall,
        qdrant_reachable=qdrant_ok,
        minio_reachable=minio_ok,
        scheduler_running=scheduler_ok,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics.

    Returns:
        Prometheus-formatted metrics text.
    """
    # Refresh collection vector counts
    try:
        await fetch_collection_stats()
    except Exception:
        pass

    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=6335,
        log_level="info",
        access_log=True,
    )
