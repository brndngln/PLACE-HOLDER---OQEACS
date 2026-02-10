#!/usr/bin/env python3
"""
SYSTEM 1 -- BACKUP FORTRESS: Backup Orchestrator
Omni Quantum Elite AI Coding System -- Data Protection Layer

FastAPI service that orchestrates Restic-based backups for all platform services.
Targets: PostgreSQL, Redis, Qdrant, Gitea, Vault, MinIO, Docker volumes,
n8n, Mattermost, Grafana, Prometheus.

Each backup: subprocess call -> restic check -> log completion -> update metrics.
Scheduling via APScheduler with configurable cron per target.
On failure: retry once after 5min -> Mattermost webhook + increment failure counter.
"""

import asyncio
import hashlib
import io
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Query
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import PlainTextResponse

from retention_manager import RetentionManager

# ---------------------------------------------------------------------------
# Structured Logging
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("backup-orchestrator")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

RESTIC_PASSWORD = os.getenv("RESTIC_PASSWORD", "omni-quantum-restic-key")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://omni-minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MATTERMOST_WEBHOOK_URL = os.getenv("MATTERMOST_WEBHOOK_URL", "")

# Database connection strings
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "omni-postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DATABASES = os.getenv("POSTGRES_DATABASES", "omni_quantum,gitea,authentik,n8n,grafana").split(",")

REDIS_HOST = os.getenv("REDIS_HOST", "omni-redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

QDRANT_HOST = os.getenv("QDRANT_HOST", "omni-qdrant")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")

GITEA_HOST = os.getenv("GITEA_HOST", "omni-gitea")
GITEA_DATA_DIR = os.getenv("GITEA_DATA_DIR", "/data/gitea")

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")

MINIO_MC_ALIAS = os.getenv("MINIO_MC_ALIAS", "omni")

N8N_HOST = os.getenv("N8N_HOST", "http://omni-n8n:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

MATTERMOST_HOST = os.getenv("MATTERMOST_HOST", "omni-mattermost")

GRAFANA_HOST = os.getenv("GRAFANA_HOST", "http://omni-grafana:3000")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", "")

PROMETHEUS_HOST = os.getenv("PROMETHEUS_HOST", "http://omni-prometheus:9090")

DOCKER_VOLUMES = os.getenv("DOCKER_VOLUMES", "").split(",") if os.getenv("DOCKER_VOLUMES") else []

BACKUP_BASE_DIR = os.getenv("BACKUP_BASE_DIR", "/tmp/backups")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://omni-master-orchestrator:8000")
UPTIME_KUMA_URL = os.getenv("UPTIME_KUMA_URL", "http://omni-uptime-kuma:3001")

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------

registry = CollectorRegistry()

backup_last_success_timestamp = Gauge(
    "backup_last_success_timestamp",
    "Unix timestamp of last successful backup",
    ["service"],
    registry=registry,
)

backup_duration_seconds = Histogram(
    "backup_duration_seconds",
    "Duration of backup jobs in seconds",
    ["service"],
    registry=registry,
    buckets=(10, 30, 60, 120, 300, 600, 1200, 1800, 3600),
)

backup_size_bytes = Gauge(
    "backup_size_bytes",
    "Size of last backup in bytes",
    ["service"],
    registry=registry,
)

backup_failures_total = Counter(
    "backup_failures_total",
    "Total number of backup failures",
    ["service"],
    registry=registry,
)

backup_snapshots_total = Gauge(
    "backup_snapshots_total",
    "Total number of snapshots stored",
    ["service"],
    registry=registry,
)

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class BackupJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    service: str
    status: str = "pending"
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    size_bytes: int | None = None
    snapshot_id: str | None = None
    error: str | None = None
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ScheduleConfig(BaseModel):
    postgresql: str = "0 */6 * * *"
    redis: str = "0 * * * *"
    qdrant: str = "0 2 * * *"
    gitea: str = "0 3 * * *"
    vault: str = "0 1 * * *"
    minio: str = "0 4 * * *"
    docker_volumes: str = "0 4 * * *"
    n8n: str = "0 4 * * *"
    mattermost: str = "0 4 * * *"
    grafana: str = "0 4 * * *"
    prometheus: str = "0 4 * * *"


class BackupResponse(BaseModel):
    status: str
    message: str
    job: BackupJob | None = None
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ErrorResponse(BaseModel):
    error: str
    detail: str
    trace_id: str


# ---------------------------------------------------------------------------
# Global State
# ---------------------------------------------------------------------------

ALL_TARGETS = [
    "postgresql", "redis", "qdrant", "gitea", "vault", "minio",
    "docker_volumes", "n8n", "mattermost", "grafana", "prometheus",
]

backup_history: list[BackupJob] = []
current_jobs: dict[str, BackupJob] = {}
current_schedule = ScheduleConfig()
scheduler = AsyncIOScheduler()
retention_manager: RetentionManager | None = None


# ---------------------------------------------------------------------------
# Restic Helpers
# ---------------------------------------------------------------------------


def _restic_env(service: str) -> dict[str, str]:
    """Build environment variables for a Restic command targeting a specific service repo."""
    repo = f"s3:{MINIO_ENDPOINT}/omni-backups-{service}"
    env = os.environ.copy()
    env.update({
        "RESTIC_REPOSITORY": repo,
        "RESTIC_PASSWORD": RESTIC_PASSWORD,
        "AWS_ACCESS_KEY_ID": MINIO_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": MINIO_SECRET_KEY,
    })
    return env


async def _run_command(cmd: list[str], env: dict[str, str] | None = None,
                       cwd: str | None = None, timeout: int = 3600) -> tuple[int, str, str]:
    """Run a subprocess asynchronously and return (returncode, stdout, stderr)."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=merged_env,
        cwd=cwd,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return -1, "", f"Command timed out after {timeout}s"

    stdout_str = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
    stderr_str = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
    return proc.returncode or 0, stdout_str, stderr_str


async def _restic_backup(service: str, source_path: str, tags: list[str] | None = None) -> tuple[str, int]:
    """Run restic backup on a path and return (snapshot_id, size_bytes)."""
    env = _restic_env(service)
    cmd = ["restic", "backup", source_path, "--json"]
    if tags:
        for tag in tags:
            cmd.extend(["--tag", tag])

    rc, stdout, stderr = await _run_command(cmd, env=env)
    if rc != 0:
        raise RuntimeError(f"restic backup failed for {service}: {stderr}")

    snapshot_id = ""
    size_bytes = 0
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        import json
        try:
            data = json.loads(line)
            if data.get("message_type") == "summary":
                snapshot_id = data.get("snapshot_id", "")
                size_bytes = data.get("total_bytes_processed", 0)
        except json.JSONDecodeError:
            continue

    if not snapshot_id:
        # Fallback: get latest snapshot
        rc2, stdout2, _ = await _run_command(
            ["restic", "snapshots", "--json", "--latest", "1"], env=env
        )
        if rc2 == 0 and stdout2.strip():
            import json
            try:
                snaps = json.loads(stdout2)
                if snaps:
                    snapshot_id = snaps[0].get("short_id", snaps[0].get("id", "unknown"))
            except json.JSONDecodeError:
                snapshot_id = "unknown"

    return snapshot_id, size_bytes


async def _restic_check(service: str) -> bool:
    """Run restic check to verify repository integrity."""
    env = _restic_env(service)
    rc, stdout, stderr = await _run_command(["restic", "check"], env=env, timeout=600)
    if rc != 0:
        logger.error("restic_check_failed", service=service, stderr=stderr)
        return False
    return True


async def _restic_snapshots_count(service: str) -> int:
    """Count total snapshots in a Restic repository."""
    env = _restic_env(service)
    rc, stdout, stderr = await _run_command(["restic", "snapshots", "--json"], env=env)
    if rc != 0:
        return 0
    import json
    try:
        snaps = json.loads(stdout)
        return len(snaps) if isinstance(snaps, list) else 0
    except json.JSONDecodeError:
        return 0


async def _restic_delete_snapshot(service: str, snapshot_id: str) -> bool:
    """Delete a specific snapshot from a Restic repository."""
    env = _restic_env(service)
    rc, stdout, stderr = await _run_command(
        ["restic", "forget", snapshot_id, "--prune"], env=env, timeout=600
    )
    if rc != 0:
        logger.error("restic_delete_failed", service=service, snapshot_id=snapshot_id, stderr=stderr)
        return False
    return True


# ---------------------------------------------------------------------------
# Mattermost Notification
# ---------------------------------------------------------------------------


async def _notify_mattermost(message: str) -> None:
    """Post a notification message to Mattermost via webhook."""
    if not MATTERMOST_WEBHOOK_URL:
        logger.warning("mattermost_webhook_not_configured")
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(MATTERMOST_WEBHOOK_URL, json={"text": message})
            if resp.status_code >= 400:
                logger.error("mattermost_notification_failed", status=resp.status_code)
    except Exception as exc:
        logger.error("mattermost_notification_error", error=str(exc))


# ---------------------------------------------------------------------------
# Backup Functions per Target
# ---------------------------------------------------------------------------


async def _backup_postgresql() -> tuple[str, int]:
    """Dump all configured PostgreSQL databases with pg_dump, then backup with Restic."""
    log = logger.bind(service="postgresql")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "postgresql")
    os.makedirs(dump_dir, exist_ok=True)

    total_size = 0
    pg_env = os.environ.copy()
    pg_env["PGPASSWORD"] = POSTGRES_PASSWORD

    for db in POSTGRES_DATABASES:
        db = db.strip()
        if not db:
            continue
        dump_file = os.path.join(dump_dir, f"{db}.sql.gz")
        log.info("dumping_database", database=db)

        # pg_dump | gzip
        dump_cmd = (
            f"pg_dump -h {POSTGRES_HOST} -p {POSTGRES_PORT} -U {POSTGRES_USER} "
            f"-d {db} --format=custom --compress=6 -f {dump_file}"
        )
        rc, stdout, stderr = await _run_command(
            ["sh", "-c", dump_cmd],
            env=pg_env,
            timeout=1800,
        )
        if rc != 0:
            raise RuntimeError(f"pg_dump failed for {db}: {stderr}")

        if os.path.exists(dump_file):
            total_size += os.path.getsize(dump_file)
        log.info("database_dumped", database=db, file=dump_file)

    snapshot_id, restic_size = await _restic_backup(
        "postgresql", dump_dir, tags=["postgresql", "automated"]
    )

    # Cleanup dump files
    for f in os.listdir(dump_dir):
        os.remove(os.path.join(dump_dir, f))

    return snapshot_id, restic_size or total_size


async def _backup_redis() -> tuple[str, int]:
    """Trigger BGSAVE on Redis, copy RDB file, then backup with Restic."""
    log = logger.bind(service="redis")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "redis")
    os.makedirs(dump_dir, exist_ok=True)

    # Trigger BGSAVE
    auth_flag = f"-a {REDIS_PASSWORD}" if REDIS_PASSWORD else ""
    bgsave_cmd = f"redis-cli -h {REDIS_HOST} -p {REDIS_PORT} {auth_flag} BGSAVE"
    rc, stdout, stderr = await _run_command(["sh", "-c", bgsave_cmd])
    if rc != 0:
        raise RuntimeError(f"Redis BGSAVE failed: {stderr}")

    log.info("bgsave_triggered", response=stdout.strip())

    # Wait for BGSAVE to complete
    for _ in range(60):
        check_cmd = f"redis-cli -h {REDIS_HOST} -p {REDIS_PORT} {auth_flag} LASTSAVE"
        rc, stdout, stderr = await _run_command(["sh", "-c", check_cmd])
        if rc == 0:
            break
        await asyncio.sleep(1)

    # Copy RDB file from Redis container
    rdb_dest = os.path.join(dump_dir, "dump.rdb")
    copy_cmd = f"docker cp omni-redis:/data/dump.rdb {rdb_dest}"
    rc, stdout, stderr = await _run_command(["sh", "-c", copy_cmd])
    if rc != 0:
        raise RuntimeError(f"Failed to copy Redis RDB: {stderr}")

    size = os.path.getsize(rdb_dest) if os.path.exists(rdb_dest) else 0
    log.info("rdb_copied", file=rdb_dest, size=size)

    snapshot_id, restic_size = await _restic_backup(
        "redis", dump_dir, tags=["redis", "automated"]
    )

    # Cleanup
    if os.path.exists(rdb_dest):
        os.remove(rdb_dest)

    return snapshot_id, restic_size or size


async def _backup_qdrant() -> tuple[str, int]:
    """Create Qdrant snapshot via API, download it, then backup with Restic."""
    log = logger.bind(service="qdrant")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "qdrant")
    os.makedirs(dump_dir, exist_ok=True)

    qdrant_url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

    async with httpx.AsyncClient(timeout=120) as client:
        # List all collections
        resp = await client.get(f"{qdrant_url}/collections")
        resp.raise_for_status()
        collections_data = resp.json()
        collections = [c["name"] for c in collections_data.get("result", {}).get("collections", [])]

        total_size = 0
        for collection in collections:
            log.info("snapshotting_collection", collection=collection)

            # Create snapshot
            snap_resp = await client.post(f"{qdrant_url}/collections/{collection}/snapshots")
            snap_resp.raise_for_status()
            snap_data = snap_resp.json()
            snap_name = snap_data.get("result", {}).get("name", "")

            if not snap_name:
                log.warning("no_snapshot_name", collection=collection)
                continue

            # Download snapshot
            dl_resp = await client.get(
                f"{qdrant_url}/collections/{collection}/snapshots/{snap_name}"
            )
            dl_resp.raise_for_status()

            snap_file = os.path.join(dump_dir, f"{collection}_{snap_name}")
            with open(snap_file, "wb") as f:
                f.write(dl_resp.content)

            file_size = os.path.getsize(snap_file)
            total_size += file_size
            log.info("snapshot_downloaded", collection=collection, size=file_size)

            # Delete remote snapshot to save space
            await client.delete(f"{qdrant_url}/collections/{collection}/snapshots/{snap_name}")

    snapshot_id, restic_size = await _restic_backup(
        "qdrant", dump_dir, tags=["qdrant", "automated"]
    )

    # Cleanup
    for f in os.listdir(dump_dir):
        os.remove(os.path.join(dump_dir, f))

    return snapshot_id, restic_size or total_size


async def _backup_gitea() -> tuple[str, int]:
    """Run gitea dump inside the Gitea container, then backup with Restic."""
    log = logger.bind(service="gitea")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "gitea")
    os.makedirs(dump_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dump_file = f"gitea-dump-{timestamp}.zip"

    # Execute gitea dump inside the container
    rc, stdout, stderr = await _run_command([
        "docker", "exec", "omni-gitea",
        "gitea", "dump",
        "--file", f"/tmp/{dump_file}",
        "--type", "zip",
    ], timeout=1800)

    if rc != 0:
        raise RuntimeError(f"gitea dump failed: {stderr}")

    log.info("gitea_dump_created", file=dump_file)

    # Copy dump out of container
    local_dump = os.path.join(dump_dir, dump_file)
    rc, stdout, stderr = await _run_command([
        "docker", "cp", f"omni-gitea:/tmp/{dump_file}", local_dump,
    ])
    if rc != 0:
        raise RuntimeError(f"Failed to copy gitea dump: {stderr}")

    # Clean up inside container
    await _run_command(["docker", "exec", "omni-gitea", "rm", f"/tmp/{dump_file}"])

    size = os.path.getsize(local_dump) if os.path.exists(local_dump) else 0
    log.info("gitea_dump_copied", size=size)

    snapshot_id, restic_size = await _restic_backup(
        "gitea", dump_dir, tags=["gitea", "automated"]
    )

    # Cleanup
    if os.path.exists(local_dump):
        os.remove(local_dump)

    return snapshot_id, restic_size or size


async def _backup_vault() -> tuple[str, int]:
    """Take a Vault Raft snapshot, then backup with Restic."""
    log = logger.bind(service="vault")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "vault")
    os.makedirs(dump_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snap_file = os.path.join(dump_dir, f"vault-raft-{timestamp}.snap")

    vault_env = os.environ.copy()
    vault_env["VAULT_ADDR"] = VAULT_ADDR
    vault_env["VAULT_TOKEN"] = VAULT_TOKEN

    rc, stdout, stderr = await _run_command([
        "vault", "operator", "raft", "snapshot", "save", snap_file,
    ], env=vault_env, timeout=300)

    if rc != 0:
        # Fallback: try via API
        log.warning("vault_cli_snapshot_failed", stderr=stderr)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"{VAULT_ADDR}/v1/sys/storage/raft/snapshot",
                headers={"X-Vault-Token": VAULT_TOKEN},
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Vault snapshot API failed: {resp.status_code} {resp.text}")
            with open(snap_file, "wb") as f:
                f.write(resp.content)

    size = os.path.getsize(snap_file) if os.path.exists(snap_file) else 0
    log.info("vault_snapshot_created", size=size)

    snapshot_id, restic_size = await _restic_backup(
        "vault", dump_dir, tags=["vault", "automated"]
    )

    # Cleanup
    if os.path.exists(snap_file):
        os.remove(snap_file)

    return snapshot_id, restic_size or size


async def _backup_minio() -> tuple[str, int]:
    """Mirror MinIO data using mc, then backup with Restic."""
    log = logger.bind(service="minio")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "minio")
    os.makedirs(dump_dir, exist_ok=True)

    # Configure mc alias
    rc, stdout, stderr = await _run_command([
        "mc", "alias", "set", MINIO_MC_ALIAS,
        MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
    ])
    if rc != 0:
        raise RuntimeError(f"mc alias set failed: {stderr}")

    # Mirror all buckets (excluding backup buckets to avoid recursion)
    rc, stdout, stderr = await _run_command([
        "mc", "mirror", "--overwrite",
        "--exclude", "omni-backups-*/**",
        f"{MINIO_MC_ALIAS}/", dump_dir,
    ], timeout=3600)
    if rc != 0:
        raise RuntimeError(f"mc mirror failed: {stderr}")

    # Calculate total size
    total_size = 0
    for root, dirs, files in os.walk(dump_dir):
        for fname in files:
            total_size += os.path.getsize(os.path.join(root, fname))

    log.info("minio_mirrored", total_size=total_size)

    snapshot_id, restic_size = await _restic_backup(
        "minio", dump_dir, tags=["minio", "automated"]
    )

    # Cleanup mirror directory
    import shutil
    shutil.rmtree(dump_dir, ignore_errors=True)
    os.makedirs(dump_dir, exist_ok=True)

    return snapshot_id, restic_size or total_size


async def _backup_docker_volumes() -> tuple[str, int]:
    """Backup Docker named volumes by mounting them in a temp container and using Restic."""
    log = logger.bind(service="docker_volumes")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "docker_volumes")
    os.makedirs(dump_dir, exist_ok=True)

    volumes_to_backup = DOCKER_VOLUMES
    if not volumes_to_backup or volumes_to_backup == [""]:
        # Auto-discover volumes
        rc, stdout, stderr = await _run_command([
            "docker", "volume", "ls", "--format", "{{.Name}}",
        ])
        if rc == 0:
            volumes_to_backup = [
                v.strip() for v in stdout.strip().split("\n")
                if v.strip() and not v.strip().startswith("omni-backups")
            ]

    total_size = 0
    for volume in volumes_to_backup:
        volume = volume.strip()
        if not volume:
            continue

        log.info("backing_up_volume", volume=volume)
        vol_dir = os.path.join(dump_dir, volume)
        os.makedirs(vol_dir, exist_ok=True)

        # Use a temp container to mount and tar the volume
        tar_file = os.path.join(vol_dir, f"{volume}.tar.gz")
        rc, stdout, stderr = await _run_command([
            "docker", "run", "--rm",
            "-v", f"{volume}:/source:ro",
            "-v", f"{vol_dir}:/backup",
            "alpine:latest",
            "tar", "czf", f"/backup/{volume}.tar.gz", "-C", "/source", ".",
        ], timeout=600)

        if rc != 0:
            log.warning("volume_backup_failed", volume=volume, stderr=stderr)
            continue

        if os.path.exists(tar_file):
            fsize = os.path.getsize(tar_file)
            total_size += fsize
            log.info("volume_backed_up", volume=volume, size=fsize)

    snapshot_id, restic_size = await _restic_backup(
        "docker_volumes", dump_dir, tags=["docker_volumes", "automated"]
    )

    # Cleanup
    import shutil
    shutil.rmtree(dump_dir, ignore_errors=True)
    os.makedirs(dump_dir, exist_ok=True)

    return snapshot_id, restic_size or total_size


async def _backup_n8n() -> tuple[str, int]:
    """Export all n8n workflows via the API, then backup with Restic."""
    log = logger.bind(service="n8n")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "n8n")
    os.makedirs(dump_dir, exist_ok=True)

    import json

    headers = {}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY

    async with httpx.AsyncClient(timeout=60) as client:
        # Export workflows
        resp = await client.get(f"{N8N_HOST}/api/v1/workflows", headers=headers)
        resp.raise_for_status()
        workflows = resp.json().get("data", [])

        workflows_file = os.path.join(dump_dir, "workflows.json")
        with open(workflows_file, "w") as f:
            json.dump(workflows, f, indent=2)
        log.info("workflows_exported", count=len(workflows))

        # Export credentials metadata (not secrets)
        try:
            creds_resp = await client.get(f"{N8N_HOST}/api/v1/credentials", headers=headers)
            creds_resp.raise_for_status()
            creds = creds_resp.json().get("data", [])
            creds_file = os.path.join(dump_dir, "credentials_metadata.json")
            with open(creds_file, "w") as f:
                json.dump(creds, f, indent=2)
            log.info("credentials_metadata_exported", count=len(creds))
        except Exception as exc:
            log.warning("credentials_export_failed", error=str(exc))

    total_size = sum(
        os.path.getsize(os.path.join(dump_dir, f))
        for f in os.listdir(dump_dir)
        if os.path.isfile(os.path.join(dump_dir, f))
    )

    snapshot_id, restic_size = await _restic_backup(
        "n8n", dump_dir, tags=["n8n", "automated"]
    )

    # Cleanup
    for f in os.listdir(dump_dir):
        os.remove(os.path.join(dump_dir, f))

    return snapshot_id, restic_size or total_size


async def _backup_mattermost() -> tuple[str, int]:
    """Export Mattermost data via mmctl, then backup with Restic."""
    log = logger.bind(service="mattermost")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "mattermost")
    os.makedirs(dump_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Create export via mmctl inside the container
    rc, stdout, stderr = await _run_command([
        "docker", "exec", "omni-mattermost",
        "mmctl", "export", "create",
        "--local",
    ], timeout=600)

    if rc != 0:
        raise RuntimeError(f"mmctl export create failed: {stderr}")

    log.info("mattermost_export_created", output=stdout.strip())

    # Wait for export to complete and list exports
    await asyncio.sleep(5)
    rc, stdout, stderr = await _run_command([
        "docker", "exec", "omni-mattermost",
        "mmctl", "export", "list",
        "--local",
    ])

    export_file = ""
    if rc == 0 and stdout.strip():
        lines = stdout.strip().split("\n")
        if lines:
            export_file = lines[-1].strip()

    if export_file:
        # Download export
        local_file = os.path.join(dump_dir, f"mattermost-export-{timestamp}.zip")
        rc, stdout, stderr = await _run_command([
            "docker", "exec", "omni-mattermost",
            "mmctl", "export", "download", export_file,
            "--local",
        ], timeout=600)

        # Copy from container
        rc, stdout, stderr = await _run_command([
            "docker", "cp",
            f"omni-mattermost:/opt/mattermost/data/export/{export_file}",
            local_file,
        ])

        if rc != 0:
            log.warning("mattermost_export_copy_failed", stderr=stderr)
            # Try alternate path
            rc, stdout, stderr = await _run_command([
                "docker", "cp",
                f"omni-mattermost:/mattermost/data/{export_file}",
                local_file,
            ])

        # Delete export from container
        await _run_command([
            "docker", "exec", "omni-mattermost",
            "mmctl", "export", "delete", export_file,
            "--local",
        ])

    total_size = sum(
        os.path.getsize(os.path.join(dump_dir, f))
        for f in os.listdir(dump_dir)
        if os.path.isfile(os.path.join(dump_dir, f))
    )

    log.info("mattermost_export_ready", size=total_size)

    snapshot_id, restic_size = await _restic_backup(
        "mattermost", dump_dir, tags=["mattermost", "automated"]
    )

    # Cleanup
    for f in os.listdir(dump_dir):
        fpath = os.path.join(dump_dir, f)
        if os.path.isfile(fpath):
            os.remove(fpath)

    return snapshot_id, restic_size or total_size


async def _backup_grafana() -> tuple[str, int]:
    """Export all Grafana dashboards as JSON via the API, then backup with Restic."""
    log = logger.bind(service="grafana")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "grafana")
    os.makedirs(dump_dir, exist_ok=True)

    import json

    headers = {}
    if GRAFANA_API_KEY:
        headers["Authorization"] = f"Bearer {GRAFANA_API_KEY}"

    async with httpx.AsyncClient(timeout=60) as client:
        # Search for all dashboards
        resp = await client.get(f"{GRAFANA_HOST}/api/search?type=dash-db&limit=5000", headers=headers)
        resp.raise_for_status()
        dashboards = resp.json()
        log.info("dashboards_found", count=len(dashboards))

        exported = []
        for dash in dashboards:
            uid = dash.get("uid", "")
            if not uid:
                continue

            try:
                dash_resp = await client.get(f"{GRAFANA_HOST}/api/dashboards/uid/{uid}", headers=headers)
                dash_resp.raise_for_status()
                dash_data = dash_resp.json()

                safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in dash.get("title", uid))
                dash_file = os.path.join(dump_dir, f"{safe_title}_{uid}.json")
                with open(dash_file, "w") as f:
                    json.dump(dash_data, f, indent=2)
                exported.append(uid)
            except Exception as exc:
                log.warning("dashboard_export_failed", uid=uid, error=str(exc))

        log.info("dashboards_exported", count=len(exported))

        # Export datasources
        try:
            ds_resp = await client.get(f"{GRAFANA_HOST}/api/datasources", headers=headers)
            ds_resp.raise_for_status()
            ds_file = os.path.join(dump_dir, "datasources.json")
            with open(ds_file, "w") as f:
                json.dump(ds_resp.json(), f, indent=2)
            log.info("datasources_exported")
        except Exception as exc:
            log.warning("datasources_export_failed", error=str(exc))

        # Export alert rules
        try:
            alert_resp = await client.get(f"{GRAFANA_HOST}/api/v1/provisioning/alert-rules", headers=headers)
            alert_resp.raise_for_status()
            alert_file = os.path.join(dump_dir, "alert_rules.json")
            with open(alert_file, "w") as f:
                json.dump(alert_resp.json(), f, indent=2)
            log.info("alert_rules_exported")
        except Exception as exc:
            log.warning("alert_rules_export_failed", error=str(exc))

    total_size = sum(
        os.path.getsize(os.path.join(dump_dir, f))
        for f in os.listdir(dump_dir)
        if os.path.isfile(os.path.join(dump_dir, f))
    )

    snapshot_id, restic_size = await _restic_backup(
        "grafana", dump_dir, tags=["grafana", "automated"]
    )

    # Cleanup
    for f in os.listdir(dump_dir):
        fpath = os.path.join(dump_dir, f)
        if os.path.isfile(fpath):
            os.remove(fpath)

    return snapshot_id, restic_size or total_size


async def _backup_prometheus() -> tuple[str, int]:
    """Create a Prometheus snapshot via the admin API, then backup with Restic."""
    log = logger.bind(service="prometheus")
    dump_dir = os.path.join(BACKUP_BASE_DIR, "prometheus")
    os.makedirs(dump_dir, exist_ok=True)

    async with httpx.AsyncClient(timeout=120) as client:
        # Create snapshot via admin API
        resp = await client.post(f"{PROMETHEUS_HOST}/api/v1/admin/tsdb/snapshot")
        resp.raise_for_status()
        snap_data = resp.json()
        snap_name = snap_data.get("data", {}).get("name", "")

        if not snap_name:
            raise RuntimeError("Prometheus snapshot API returned no snapshot name")

        log.info("prometheus_snapshot_created", snapshot=snap_name)

    # Copy snapshot from Prometheus container
    snap_dest = os.path.join(dump_dir, snap_name)
    os.makedirs(snap_dest, exist_ok=True)

    rc, stdout, stderr = await _run_command([
        "docker", "cp",
        f"omni-prometheus:/prometheus/snapshots/{snap_name}/.",
        snap_dest,
    ], timeout=600)

    if rc != 0:
        raise RuntimeError(f"Failed to copy Prometheus snapshot: {stderr}")

    # Calculate size
    total_size = 0
    for root, dirs, files in os.walk(snap_dest):
        for fname in files:
            total_size += os.path.getsize(os.path.join(root, fname))

    log.info("prometheus_snapshot_copied", size=total_size)

    snapshot_id, restic_size = await _restic_backup(
        "prometheus", dump_dir, tags=["prometheus", "automated"]
    )

    # Cleanup local copy
    import shutil
    shutil.rmtree(dump_dir, ignore_errors=True)
    os.makedirs(dump_dir, exist_ok=True)

    # Delete snapshot from Prometheus container
    await _run_command([
        "docker", "exec", "omni-prometheus",
        "rm", "-rf", f"/prometheus/snapshots/{snap_name}",
    ])

    return snapshot_id, restic_size or total_size


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

BACKUP_FUNCTIONS: dict[str, Any] = {
    "postgresql": _backup_postgresql,
    "redis": _backup_redis,
    "qdrant": _backup_qdrant,
    "gitea": _backup_gitea,
    "vault": _backup_vault,
    "minio": _backup_minio,
    "docker_volumes": _backup_docker_volumes,
    "n8n": _backup_n8n,
    "mattermost": _backup_mattermost,
    "grafana": _backup_grafana,
    "prometheus": _backup_prometheus,
}


async def _execute_backup(service: str, is_retry: bool = False) -> BackupJob:
    """Execute a backup job for a single service with full lifecycle logging."""
    trace_id = str(uuid.uuid4())
    log = logger.bind(service=service, trace_id=trace_id, is_retry=is_retry)

    job = BackupJob(
        service=service,
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        trace_id=trace_id,
    )
    current_jobs[service] = job

    log.info("backup_started")
    start_time = time.monotonic()

    try:
        backup_fn = BACKUP_FUNCTIONS.get(service)
        if not backup_fn:
            raise ValueError(f"Unknown backup target: {service}")

        snapshot_id, size_bytes = await backup_fn()

        # Verify with restic check
        log.info("running_restic_check")
        check_ok = await _restic_check(service)
        if not check_ok:
            raise RuntimeError(f"restic check failed for {service} after backup")

        duration = time.monotonic() - start_time
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc).isoformat()
        job.duration_seconds = round(duration, 2)
        job.size_bytes = size_bytes
        job.snapshot_id = snapshot_id

        # Update Prometheus metrics
        backup_last_success_timestamp.labels(service=service).set(time.time())
        backup_duration_seconds.labels(service=service).observe(duration)
        backup_size_bytes.labels(service=service).set(size_bytes)

        # Update snapshot count
        snap_count = await _restic_snapshots_count(service)
        backup_snapshots_total.labels(service=service).set(snap_count)

        log.info(
            "backup_completed",
            duration_seconds=job.duration_seconds,
            size_bytes=size_bytes,
            snapshot_id=snapshot_id,
            snapshots_total=snap_count,
        )

    except Exception as exc:
        duration = time.monotonic() - start_time
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc).isoformat()
        job.duration_seconds = round(duration, 2)
        job.error = str(exc)

        log.error("backup_failed", error=str(exc), duration_seconds=job.duration_seconds)

        if not is_retry:
            # Schedule retry after 5 minutes
            log.info("scheduling_retry", delay_seconds=300)
            await asyncio.sleep(300)
            retry_job = await _execute_backup(service, is_retry=True)
            if retry_job.status == "completed":
                return retry_job

        # If retry also failed or this is already a retry, notify
        backup_failures_total.labels(service=service).inc()
        await _notify_mattermost(
            f":warning: **Backup Failed: {service}**\n"
            f"- Error: `{str(exc)[:200]}`\n"
            f"- Duration: {job.duration_seconds}s\n"
            f"- Trace ID: `{trace_id}`\n"
            f"- Retry: {'Yes (also failed)' if is_retry else 'Scheduled'}"
        )

    finally:
        current_jobs.pop(service, None)
        backup_history.append(job)
        # Trim history to 30 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        cutoff_str = cutoff.isoformat()
        while backup_history and backup_history[0].started_at and backup_history[0].started_at < cutoff_str:
            backup_history.pop(0)

    return job


async def _execute_backup_all() -> list[BackupJob]:
    """Execute backups for all targets sequentially."""
    results = []
    for service in ALL_TARGETS:
        job = await _execute_backup(service)
        results.append(job)
    return results


# ---------------------------------------------------------------------------
# Scheduler Setup
# ---------------------------------------------------------------------------


def _setup_scheduler() -> None:
    """Configure APScheduler with cron jobs for each backup target."""
    schedule = current_schedule

    target_crons = {
        "postgresql": schedule.postgresql,
        "redis": schedule.redis,
        "qdrant": schedule.qdrant,
        "gitea": schedule.gitea,
        "vault": schedule.vault,
        "minio": schedule.minio,
        "docker_volumes": schedule.docker_volumes,
        "n8n": schedule.n8n,
        "mattermost": schedule.mattermost,
        "grafana": schedule.grafana,
        "prometheus": schedule.prometheus,
    }

    # Remove existing jobs
    for job in scheduler.get_jobs():
        if job.id.startswith("backup_"):
            scheduler.remove_job(job.id)

    for service, cron_expr in target_crons.items():
        parts = cron_expr.split()
        if len(parts) != 5:
            logger.warning("invalid_cron", service=service, cron=cron_expr)
            continue

        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
        )

        scheduler.add_job(
            _execute_backup,
            trigger,
            args=[service],
            id=f"backup_{service}",
            name=f"Backup {service}",
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info("scheduled_backup", service=service, cron=cron_expr)


def _setup_retention_scheduler() -> None:
    """Schedule retention pruning to run daily at 6AM."""
    global retention_manager
    retention_manager = RetentionManager(
        minio_endpoint=MINIO_ENDPOINT,
        minio_access_key=MINIO_ACCESS_KEY,
        minio_secret_key=MINIO_SECRET_KEY,
        restic_password=RESTIC_PASSWORD,
        targets=ALL_TARGETS,
        registry=registry,
    )

    scheduler.add_job(
        retention_manager.run_retention,
        CronTrigger(hour=6, minute=0),
        id="retention_prune",
        name="Retention Pruning",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("scheduled_retention", cron="0 6 * * *")


# ---------------------------------------------------------------------------
# Confirmation Token (for destructive DELETE operations)
# ---------------------------------------------------------------------------


def _generate_confirmation_token(service: str, snapshot_id: str) -> str:
    """Generate a deterministic confirmation token for snapshot deletion."""
    secret = RESTIC_PASSWORD
    raw = f"{service}:{snapshot_id}:{secret}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start scheduler on startup, shut down on exit."""
    logger.info("starting_backup_orchestrator")
    _setup_scheduler()
    _setup_retention_scheduler()
    scheduler.start()
    logger.info("scheduler_started")
    yield
    scheduler.shutdown(wait=False)
    logger.info("scheduler_stopped")


app = FastAPI(
    title="Backup Fortress -- Backup Orchestrator",
    description="SYSTEM 1: Restic-based backup orchestration for all Omni Quantum services",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    trace_id = str(uuid.uuid4())
    logger.error(
        "unhandled_exception",
        trace_id=trace_id,
        error=str(exc),
        path=str(request.url),
    )
    return {
        "error": type(exc).__name__,
        "detail": str(exc),
        "trace_id": trace_id,
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    trace_id = str(uuid.uuid4())
    return {
        "error": "HTTPException",
        "detail": exc.detail,
        "trace_id": trace_id,
    }


# ---------------------------------------------------------------------------
# Health / Ready / Metrics
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "healthy", "service": "backup-orchestrator", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/ready")
async def ready():
    """Readiness probe. Checks scheduler is running."""
    is_running = scheduler.running
    if not is_running:
        raise HTTPException(status_code=503, detail="Scheduler not running")
    return {
        "status": "ready",
        "scheduler_running": is_running,
        "jobs_count": len(scheduler.get_jobs()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        content=generate_latest(registry).decode("utf-8"),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# Backup Endpoints
# ---------------------------------------------------------------------------


@app.post("/backup/all", response_model=BackupResponse)
async def trigger_backup_all():
    """Trigger backup for all targets asynchronously."""
    trace_id = str(uuid.uuid4())
    logger.info("backup_all_triggered", trace_id=trace_id)

    # Run in background
    asyncio.create_task(_execute_backup_all())

    return BackupResponse(
        status="accepted",
        message="Backup for all targets has been initiated",
        trace_id=trace_id,
    )


@app.post("/backup/{service_name}", response_model=BackupResponse)
async def trigger_backup(service_name: str):
    """Trigger backup for a specific service."""
    if service_name not in BACKUP_FUNCTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown backup target: {service_name}. Valid targets: {', '.join(ALL_TARGETS)}",
        )

    if service_name in current_jobs:
        raise HTTPException(
            status_code=409,
            detail=f"Backup already running for {service_name}",
        )

    trace_id = str(uuid.uuid4())
    logger.info("backup_triggered", service=service_name, trace_id=trace_id)

    # Run in background
    asyncio.create_task(_execute_backup(service_name))

    return BackupResponse(
        status="accepted",
        message=f"Backup initiated for {service_name}",
        trace_id=trace_id,
    )


@app.get("/backup/status")
async def backup_status():
    """Get current status of all backup jobs."""
    active = {k: v.model_dump() for k, v in current_jobs.items()}
    return {
        "active_jobs": active,
        "active_count": len(active),
        "scheduler_running": scheduler.running,
        "scheduled_jobs": [
            {
                "id": j.id,
                "name": j.name,
                "next_run": str(j.next_run_time) if j.next_run_time else None,
            }
            for j in scheduler.get_jobs()
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/backup/history")
async def backup_history_endpoint(days: int = Query(default=30, ge=1, le=365)):
    """Get backup history for the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    filtered = [
        j.model_dump() for j in backup_history
        if j.started_at and j.started_at >= cutoff_str
    ]

    return {
        "history": filtered,
        "total_count": len(filtered),
        "days": days,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/backup/schedule")
async def get_schedule():
    """View current backup schedule."""
    return {
        "schedule": current_schedule.model_dump(),
        "scheduled_jobs": [
            {
                "id": j.id,
                "name": j.name,
                "next_run": str(j.next_run_time) if j.next_run_time else None,
                "trigger": str(j.trigger),
            }
            for j in scheduler.get_jobs()
            if j.id.startswith("backup_")
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.put("/backup/schedule")
async def update_schedule(config: ScheduleConfig):
    """Update backup schedule configuration."""
    global current_schedule
    current_schedule = config
    _setup_scheduler()
    logger.info("schedule_updated", schedule=config.model_dump())
    return {
        "status": "updated",
        "schedule": current_schedule.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.delete("/backup/{service_name}/{snapshot_id}")
async def delete_snapshot(
    service_name: str,
    snapshot_id: str,
    confirmation_token: str = Query(..., description="Confirmation token for deletion"),
):
    """Delete a specific backup snapshot. Requires a valid confirmation_token."""
    if service_name not in BACKUP_FUNCTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown backup target: {service_name}",
        )

    expected_token = _generate_confirmation_token(service_name, snapshot_id)
    if confirmation_token != expected_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid confirmation token",
        )

    trace_id = str(uuid.uuid4())
    logger.info("snapshot_delete_requested", service=service_name, snapshot_id=snapshot_id, trace_id=trace_id)

    success = await _restic_delete_snapshot(service_name, snapshot_id)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete snapshot {snapshot_id} from {service_name}",
        )

    # Update snapshot count
    snap_count = await _restic_snapshots_count(service_name)
    backup_snapshots_total.labels(service=service_name).set(snap_count)

    logger.info("snapshot_deleted", service=service_name, snapshot_id=snapshot_id, trace_id=trace_id)

    return {
        "status": "deleted",
        "service": service_name,
        "snapshot_id": snapshot_id,
        "remaining_snapshots": snap_count,
        "trace_id": trace_id,
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
    )
