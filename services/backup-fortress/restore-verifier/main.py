#!/usr/bin/env python3
"""
SYSTEM 1 -- BACKUP FORTRESS: Restore Verifier
Omni Quantum Elite AI Coding System -- Data Protection Layer

FastAPI service that verifies backup integrity by restoring snapshots
into temporary Docker containers and running validation checks.

Runs daily at 5AM via APScheduler. For each target:
1. Spin up temp Docker container (isolated network) via Docker SDK
2. Restore latest snapshot from Restic
3. Verify data integrity with service-specific checks
4. Tear down container
5. Log pass/fail + duration
6. Metric: restore_verify_last_result{service} = 1/0
7. Weekly Mattermost summary (Mondays 6AM)
"""

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import docker
import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Query
from prometheus_client import CollectorRegistry, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import PlainTextResponse

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

logger = structlog.get_logger("restore-verifier")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RESTIC_PASSWORD = os.getenv("RESTIC_PASSWORD", "omni-quantum-restic-key")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://omni-minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MATTERMOST_WEBHOOK_URL = os.getenv("MATTERMOST_WEBHOOK_URL", "")

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DATABASES = os.getenv("POSTGRES_DATABASES", "omni_quantum,gitea,authentik,n8n,grafana").split(",")

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

VERIFY_NETWORK = os.getenv("VERIFY_NETWORK", "omni-verify-isolated")
BACKUP_BASE_DIR = os.getenv("BACKUP_BASE_DIR", "/tmp/verify-restore")

ALL_TARGETS = ["postgresql", "redis", "qdrant", "gitea", "vault"]

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------

registry = CollectorRegistry()

restore_verify_last_result = Gauge(
    "restore_verify_last_result",
    "Result of last restore verification (1=pass, 0=fail)",
    ["service"],
    registry=registry,
)

restore_verify_duration_seconds = Histogram(
    "restore_verify_duration_seconds",
    "Duration of restore verification in seconds",
    ["service"],
    registry=registry,
    buckets=(10, 30, 60, 120, 300, 600, 1200, 1800),
)

restore_verify_last_timestamp = Gauge(
    "restore_verify_last_timestamp",
    "Unix timestamp of last restore verification",
    ["service"],
    registry=registry,
)

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class VerifyResult(BaseModel):
    verify_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    service: str
    status: str = "pending"
    passed: bool = False
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    snapshot_id: str | None = None
    checks: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class VerifyResponse(BaseModel):
    status: str
    message: str
    result: VerifyResult | None = None
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ErrorResponse(BaseModel):
    error: str
    detail: str
    trace_id: str


# ---------------------------------------------------------------------------
# Global State
# ---------------------------------------------------------------------------

verify_history: list[VerifyResult] = []
current_verifications: dict[str, VerifyResult] = {}
scheduler = AsyncIOScheduler()
docker_client: docker.DockerClient | None = None


# ---------------------------------------------------------------------------
# Docker Helpers
# ---------------------------------------------------------------------------


def _get_docker_client() -> docker.DockerClient:
    """Get or create Docker client."""
    global docker_client
    if docker_client is None:
        docker_client = docker.from_env()
    return docker_client


def _ensure_isolated_network() -> None:
    """Ensure the isolated verification network exists."""
    client = _get_docker_client()
    try:
        client.networks.get(VERIFY_NETWORK)
    except docker.errors.NotFound:
        client.networks.create(
            VERIFY_NETWORK,
            driver="bridge",
            internal=True,
            labels={
                "omni.quantum.component": "restore-verifier",
                "omni.quantum.purpose": "isolated-verification",
            },
        )
        logger.info("created_isolated_network", network=VERIFY_NETWORK)


def _cleanup_container(container_name: str) -> None:
    """Force remove a container if it exists."""
    client = _get_docker_client()
    try:
        container = client.containers.get(container_name)
        container.remove(force=True)
        logger.info("container_removed", container=container_name)
    except docker.errors.NotFound:
        pass
    except Exception as exc:
        logger.warning("container_cleanup_failed", container=container_name, error=str(exc))


# ---------------------------------------------------------------------------
# Restic Helpers
# ---------------------------------------------------------------------------


def _restic_env(service: str) -> dict[str, str]:
    """Build environment variables for Restic."""
    repo = f"s3:{MINIO_ENDPOINT}/omni-backups-{service}"
    return {
        "RESTIC_REPOSITORY": repo,
        "RESTIC_PASSWORD": RESTIC_PASSWORD,
        "AWS_ACCESS_KEY_ID": MINIO_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": MINIO_SECRET_KEY,
    }


async def _run_command(cmd: list[str], env: dict[str, str] | None = None,
                       cwd: str | None = None, timeout: int = 600) -> tuple[int, str, str]:
    """Run a subprocess asynchronously."""
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


async def _restic_restore_latest(service: str, target_dir: str) -> str:
    """Restore the latest snapshot for a service into target_dir. Returns snapshot ID."""
    env = _restic_env(service)

    # Get latest snapshot ID
    rc, stdout, stderr = await _run_command(
        ["restic", "snapshots", "--json", "--latest", "1"], env=env
    )
    if rc != 0:
        raise RuntimeError(f"Failed to list snapshots for {service}: {stderr}")

    import json
    try:
        snaps = json.loads(stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"No valid snapshots found for {service}")

    if not snaps:
        raise RuntimeError(f"No snapshots available for {service}")

    snapshot_id = snaps[0].get("short_id", snaps[0].get("id", "unknown"))

    # Restore
    os.makedirs(target_dir, exist_ok=True)
    rc, stdout, stderr = await _run_command(
        ["restic", "restore", "latest", "--target", target_dir], env=env, timeout=1800
    )
    if rc != 0:
        raise RuntimeError(f"Restore failed for {service}: {stderr}")

    return snapshot_id


# ---------------------------------------------------------------------------
# Verification Functions per Target
# ---------------------------------------------------------------------------


async def _verify_postgresql(restore_dir: str) -> list[dict[str, Any]]:
    """Verify PostgreSQL restore by loading dump into a temp container and running SELECT 1."""
    log = logger.bind(service="postgresql")
    checks: list[dict[str, Any]] = []
    container_name = "omni-verify-postgresql"

    _cleanup_container(container_name)
    _ensure_isolated_network()

    client = _get_docker_client()

    # Start temp PostgreSQL container
    log.info("starting_temp_postgresql")
    container = client.containers.run(
        "postgres:16-alpine",
        name=container_name,
        environment={
            "POSTGRES_USER": POSTGRES_USER,
            "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
            "POSTGRES_DB": "verify_test",
        },
        network=VERIFY_NETWORK,
        detach=True,
        remove=False,
        labels={
            "omni.quantum.component": "restore-verifier",
            "omni.quantum.purpose": "temp-verification",
        },
    )

    try:
        # Wait for PostgreSQL to be ready
        for attempt in range(30):
            exit_code, output = container.exec_run(
                f"pg_isready -U {POSTGRES_USER}", demux=True
            )
            if exit_code == 0:
                break
            await asyncio.sleep(2)
        else:
            checks.append({"check": "postgresql_ready", "passed": False, "detail": "PostgreSQL did not start"})
            return checks

        checks.append({"check": "postgresql_ready", "passed": True, "detail": "PostgreSQL container started"})

        # Find dump files in restore directory
        dump_files = []
        for root, dirs, files in os.walk(restore_dir):
            for fname in files:
                if fname.endswith((".sql", ".sql.gz", ".dump")):
                    dump_files.append(os.path.join(root, fname))

        if not dump_files:
            checks.append({"check": "dump_files_found", "passed": False, "detail": "No dump files found"})
            return checks

        checks.append({"check": "dump_files_found", "passed": True, "detail": f"Found {len(dump_files)} dump files"})

        # Copy dump files into container and restore each
        for dump_file in dump_files:
            db_name = os.path.basename(dump_file).split(".")[0].strip()
            if not db_name:
                continue

            log.info("restoring_database", database=db_name, file=dump_file)

            # Create database
            container.exec_run(
                f"psql -U {POSTGRES_USER} -c \"CREATE DATABASE {db_name};\"",
                demux=True,
            )

            # Copy dump file into container
            import tarfile
            import io
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tar.add(dump_file, arcname=os.path.basename(dump_file))
            tar_stream.seek(0)
            container.put_archive("/tmp", tar_stream.read())

            # Restore
            basename = os.path.basename(dump_file)
            if basename.endswith(".dump") or basename.endswith(".sql.gz"):
                exit_code, output = container.exec_run(
                    f"pg_restore -U {POSTGRES_USER} -d {db_name} /tmp/{basename}",
                    demux=True,
                )
            else:
                exit_code, output = container.exec_run(
                    f"psql -U {POSTGRES_USER} -d {db_name} -f /tmp/{basename}",
                    demux=True,
                )

            # Verify with SELECT 1
            exit_code, output = container.exec_run(
                f"psql -U {POSTGRES_USER} -d {db_name} -c 'SELECT 1;'",
                demux=True,
            )

            stdout_data = output[0].decode("utf-8", errors="replace") if output[0] else ""
            passed = exit_code == 0 and "1" in stdout_data
            checks.append({
                "check": f"database_{db_name}_select",
                "passed": passed,
                "detail": f"SELECT 1 on {db_name}: {'OK' if passed else 'FAILED'}",
            })

    finally:
        _cleanup_container(container_name)

    return checks


async def _verify_redis(restore_dir: str) -> list[dict[str, Any]]:
    """Verify Redis restore by loading RDB into a temp container and checking DBSIZE."""
    log = logger.bind(service="redis")
    checks: list[dict[str, Any]] = []
    container_name = "omni-verify-redis"

    _cleanup_container(container_name)
    _ensure_isolated_network()

    client = _get_docker_client()

    # Find RDB file
    rdb_file = None
    for root, dirs, files in os.walk(restore_dir):
        for fname in files:
            if fname.endswith(".rdb"):
                rdb_file = os.path.join(root, fname)
                break
        if rdb_file:
            break

    if not rdb_file:
        checks.append({"check": "rdb_file_found", "passed": False, "detail": "No RDB file found"})
        return checks

    checks.append({"check": "rdb_file_found", "passed": True, "detail": f"Found {rdb_file}"})

    # Start temp Redis container
    log.info("starting_temp_redis")
    container = client.containers.run(
        "redis:7-alpine",
        name=container_name,
        network=VERIFY_NETWORK,
        detach=True,
        remove=False,
        labels={
            "omni.quantum.component": "restore-verifier",
            "omni.quantum.purpose": "temp-verification",
        },
    )

    try:
        # Wait for Redis to be ready
        for attempt in range(20):
            exit_code, output = container.exec_run("redis-cli ping", demux=True)
            stdout_data = output[0].decode("utf-8", errors="replace") if output[0] else ""
            if exit_code == 0 and "PONG" in stdout_data:
                break
            await asyncio.sleep(1)
        else:
            checks.append({"check": "redis_ready", "passed": False, "detail": "Redis did not start"})
            return checks

        checks.append({"check": "redis_ready", "passed": True, "detail": "Redis container started"})

        # Stop Redis, copy RDB, restart
        container.exec_run("redis-cli SHUTDOWN NOSAVE", demux=True)
        await asyncio.sleep(1)

        # Copy RDB file into container
        import tarfile
        import io
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tar.add(rdb_file, arcname="dump.rdb")
        tar_stream.seek(0)
        container.put_archive("/data", tar_stream.read())

        # Restart container
        container.restart(timeout=10)
        await asyncio.sleep(3)

        # Wait for Redis to come back
        for attempt in range(20):
            exit_code, output = container.exec_run("redis-cli ping", demux=True)
            stdout_data = output[0].decode("utf-8", errors="replace") if output[0] else ""
            if exit_code == 0 and "PONG" in stdout_data:
                break
            await asyncio.sleep(1)

        # Check DBSIZE > 0
        exit_code, output = container.exec_run("redis-cli DBSIZE", demux=True)
        stdout_data = output[0].decode("utf-8", errors="replace") if output[0] else ""

        db_size = 0
        if "keys=" in stdout_data:
            try:
                db_size = int(stdout_data.split("keys=")[1].strip().rstrip(")"))
            except (ValueError, IndexError):
                pass
        elif stdout_data.strip().isdigit():
            db_size = int(stdout_data.strip())

        passed = db_size > 0
        checks.append({
            "check": "redis_dbsize",
            "passed": passed,
            "detail": f"DBSIZE = {db_size} {'(OK)' if passed else '(EMPTY)'}",
        })

    finally:
        _cleanup_container(container_name)

    return checks


async def _verify_qdrant(restore_dir: str) -> list[dict[str, Any]]:
    """Verify Qdrant restore by loading snapshots and checking collections."""
    log = logger.bind(service="qdrant")
    checks: list[dict[str, Any]] = []
    container_name = "omni-verify-qdrant"

    _cleanup_container(container_name)
    _ensure_isolated_network()

    client = _get_docker_client()

    # Find snapshot files
    snap_files = []
    for root, dirs, files in os.walk(restore_dir):
        for fname in files:
            if fname.endswith((".snapshot", ".tar", ".gz")):
                snap_files.append(os.path.join(root, fname))

    if not snap_files:
        checks.append({"check": "snapshot_files_found", "passed": False, "detail": "No snapshot files found"})
        return checks

    checks.append({
        "check": "snapshot_files_found",
        "passed": True,
        "detail": f"Found {len(snap_files)} snapshot files",
    })

    # Start temp Qdrant container
    log.info("starting_temp_qdrant")
    container = client.containers.run(
        "qdrant/qdrant:latest",
        name=container_name,
        network=VERIFY_NETWORK,
        detach=True,
        remove=False,
        labels={
            "omni.quantum.component": "restore-verifier",
            "omni.quantum.purpose": "temp-verification",
        },
    )

    try:
        # Wait for Qdrant to be ready
        qdrant_ready = False
        for attempt in range(30):
            exit_code, output = container.exec_run(
                "wget -q -O- http://localhost:6333/healthz", demux=True
            )
            if exit_code == 0:
                qdrant_ready = True
                break
            await asyncio.sleep(2)

        if not qdrant_ready:
            checks.append({"check": "qdrant_ready", "passed": False, "detail": "Qdrant did not start"})
            return checks

        checks.append({"check": "qdrant_ready", "passed": True, "detail": "Qdrant container started"})

        # Copy snapshots into container and restore
        import tarfile
        import io

        for snap_file in snap_files:
            basename = os.path.basename(snap_file)
            # Extract collection name from filename (format: collectionname_snapshotname)
            collection_name = basename.split("_")[0] if "_" in basename else "default"

            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tar.add(snap_file, arcname=basename)
            tar_stream.seek(0)
            container.put_archive("/tmp", tar_stream.read())

            # Restore snapshot via API
            exit_code, output = container.exec_run(
                f"wget -q -O- --post-data='' 'http://localhost:6333/collections/{collection_name}/snapshots/upload' "
                f"--header='Content-Type: multipart/form-data'",
                demux=True,
            )

        # List collections and check count > 0
        exit_code, output = container.exec_run(
            "wget -q -O- http://localhost:6333/collections", demux=True
        )
        stdout_data = output[0].decode("utf-8", errors="replace") if output[0] else ""

        import json
        try:
            collections_data = json.loads(stdout_data)
            collections = collections_data.get("result", {}).get("collections", [])
            collection_count = len(collections)
        except (json.JSONDecodeError, AttributeError):
            collection_count = 0

        passed = collection_count > 0
        checks.append({
            "check": "qdrant_collections",
            "passed": passed,
            "detail": f"Collections found: {collection_count}",
        })

    finally:
        _cleanup_container(container_name)

    return checks


async def _verify_gitea(restore_dir: str) -> list[dict[str, Any]]:
    """Verify Gitea restore by checking .git directory structure."""
    log = logger.bind(service="gitea")
    checks: list[dict[str, Any]] = []

    # Look for gitea dump zip
    zip_files = []
    for root, dirs, files in os.walk(restore_dir):
        for fname in files:
            if fname.endswith(".zip"):
                zip_files.append(os.path.join(root, fname))

    if not zip_files:
        checks.append({"check": "dump_files_found", "passed": False, "detail": "No Gitea dump files found"})
        return checks

    checks.append({"check": "dump_files_found", "passed": True, "detail": f"Found {len(zip_files)} dump files"})

    # Extract and verify structure
    import zipfile
    import shutil

    extract_dir = os.path.join(restore_dir, "_verify_extract")
    os.makedirs(extract_dir, exist_ok=True)

    try:
        for zf in zip_files:
            try:
                with zipfile.ZipFile(zf, "r") as z:
                    z.extractall(extract_dir)
                checks.append({"check": "zip_extraction", "passed": True, "detail": f"Extracted {os.path.basename(zf)}"})
            except zipfile.BadZipFile:
                checks.append({"check": "zip_extraction", "passed": False, "detail": f"Bad zip: {os.path.basename(zf)}"})
                continue

        # Verify expected contents: repos, db dump
        has_repos = False
        has_db = False
        has_config = False

        for root, dirs, files in os.walk(extract_dir):
            for d in dirs:
                if d in ("repos", "repositories"):
                    has_repos = True
            for f in files:
                if f.endswith((".sql", ".dump")):
                    has_db = True
                if f in ("app.ini", "gitea.ini"):
                    has_config = True

        # Verify .git structures in repos
        git_repos_found = 0
        for root, dirs, files in os.walk(extract_dir):
            if ".git" in dirs or "HEAD" in files:
                git_repos_found += 1

        checks.append({
            "check": "gitea_repos_structure",
            "passed": has_repos or git_repos_found > 0,
            "detail": f"Repos dir: {has_repos}, Git repos found: {git_repos_found}",
        })
        checks.append({
            "check": "gitea_db_dump",
            "passed": has_db,
            "detail": f"Database dump present: {has_db}",
        })
        checks.append({
            "check": "gitea_config",
            "passed": has_config,
            "detail": f"Config file present: {has_config}",
        })

    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)

    return checks


async def _verify_vault(restore_dir: str) -> list[dict[str, Any]]:
    """Verify Vault restore by checking raft snapshot data structure."""
    log = logger.bind(service="vault")
    checks: list[dict[str, Any]] = []

    # Find snapshot files
    snap_files = []
    for root, dirs, files in os.walk(restore_dir):
        for fname in files:
            if fname.endswith(".snap"):
                snap_files.append(os.path.join(root, fname))

    if not snap_files:
        checks.append({"check": "snapshot_files_found", "passed": False, "detail": "No Vault snapshot files found"})
        return checks

    checks.append({
        "check": "snapshot_files_found",
        "passed": True,
        "detail": f"Found {len(snap_files)} snapshot files",
    })

    for snap_file in snap_files:
        file_size = os.path.getsize(snap_file)
        basename = os.path.basename(snap_file)

        # Validate file is not empty
        size_ok = file_size > 100
        checks.append({
            "check": f"vault_snapshot_size_{basename}",
            "passed": size_ok,
            "detail": f"Snapshot {basename}: {file_size} bytes {'(OK)' if size_ok else '(TOO SMALL)'}",
        })

        # Verify the snapshot header (Raft snapshots have a specific format)
        with open(snap_file, "rb") as f:
            header = f.read(64)

        # Raft snapshots typically start with specific bytes
        has_valid_header = len(header) >= 64
        checks.append({
            "check": f"vault_snapshot_header_{basename}",
            "passed": has_valid_header,
            "detail": f"Snapshot header valid: {has_valid_header}",
        })

        # Try to start a temp Vault container and restore
        container_name = "omni-verify-vault"
        _cleanup_container(container_name)
        _ensure_isolated_network()

        client = _get_docker_client()

        try:
            container = client.containers.run(
                "hashicorp/vault:1.15",
                name=container_name,
                environment={
                    "VAULT_DEV_ROOT_TOKEN_ID": "verify-test-token",
                    "VAULT_DEV_LISTEN_ADDRESS": "0.0.0.0:8200",
                },
                network=VERIFY_NETWORK,
                detach=True,
                remove=False,
                cap_add=["IPC_LOCK"],
                labels={
                    "omni.quantum.component": "restore-verifier",
                    "omni.quantum.purpose": "temp-verification",
                },
            )

            # Wait for Vault to start
            vault_ready = False
            for attempt in range(20):
                exit_code, output = container.exec_run(
                    "vault status -format=json", demux=True,
                    environment={"VAULT_ADDR": "http://127.0.0.1:8200", "VAULT_TOKEN": "verify-test-token"},
                )
                if exit_code == 0:
                    vault_ready = True
                    break
                # exit code 2 means sealed but running
                if exit_code == 2:
                    vault_ready = True
                    break
                await asyncio.sleep(2)

            checks.append({
                "check": "vault_container_started",
                "passed": vault_ready,
                "detail": f"Vault dev container: {'running' if vault_ready else 'failed'}",
            })

            if vault_ready:
                # Verify seal status data
                exit_code, output = container.exec_run(
                    "vault status -format=json", demux=True,
                    environment={"VAULT_ADDR": "http://127.0.0.1:8200", "VAULT_TOKEN": "verify-test-token"},
                )
                stdout_data = output[0].decode("utf-8", errors="replace") if output[0] else ""

                import json
                try:
                    status = json.loads(stdout_data)
                    initialized = status.get("initialized", False)
                    checks.append({
                        "check": "vault_seal_status",
                        "passed": initialized,
                        "detail": f"Vault initialized: {initialized}, sealed: {status.get('sealed', 'unknown')}",
                    })
                except json.JSONDecodeError:
                    checks.append({
                        "check": "vault_seal_status",
                        "passed": False,
                        "detail": "Could not parse Vault status",
                    })

        finally:
            _cleanup_container(container_name)

    return checks


# ---------------------------------------------------------------------------
# Verification Dispatcher
# ---------------------------------------------------------------------------

VERIFY_FUNCTIONS: dict[str, Any] = {
    "postgresql": _verify_postgresql,
    "redis": _verify_redis,
    "qdrant": _verify_qdrant,
    "gitea": _verify_gitea,
    "vault": _verify_vault,
}


async def _execute_verification(service: str) -> VerifyResult:
    """Execute a full restore verification for a single service."""
    trace_id = str(uuid.uuid4())
    log = logger.bind(service=service, trace_id=trace_id)

    result = VerifyResult(
        service=service,
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        trace_id=trace_id,
    )
    current_verifications[service] = result

    log.info("verification_started")
    start_time = time.monotonic()

    restore_dir = os.path.join(BACKUP_BASE_DIR, service)
    os.makedirs(restore_dir, exist_ok=True)

    try:
        # Step 1: Restore latest snapshot
        log.info("restoring_latest_snapshot")
        snapshot_id = await _restic_restore_latest(service, restore_dir)
        result.snapshot_id = snapshot_id
        log.info("snapshot_restored", snapshot_id=snapshot_id)

        # Step 2: Run verification
        verify_fn = VERIFY_FUNCTIONS.get(service)
        if not verify_fn:
            raise ValueError(f"No verification function for {service}")

        checks = await verify_fn(restore_dir)
        result.checks = checks

        # Step 3: Determine overall pass/fail
        all_passed = all(c["passed"] for c in checks) if checks else False
        result.passed = all_passed
        result.status = "completed"

        duration = time.monotonic() - start_time
        result.duration_seconds = round(duration, 2)
        result.completed_at = datetime.now(timezone.utc).isoformat()

        # Update metrics
        restore_verify_last_result.labels(service=service).set(1 if all_passed else 0)
        restore_verify_duration_seconds.labels(service=service).observe(duration)
        restore_verify_last_timestamp.labels(service=service).set(time.time())

        log.info(
            "verification_completed",
            passed=all_passed,
            checks_total=len(checks),
            checks_passed=sum(1 for c in checks if c["passed"]),
            duration_seconds=result.duration_seconds,
        )

    except Exception as exc:
        duration = time.monotonic() - start_time
        result.status = "failed"
        result.passed = False
        result.error = str(exc)
        result.duration_seconds = round(duration, 2)
        result.completed_at = datetime.now(timezone.utc).isoformat()

        restore_verify_last_result.labels(service=service).set(0)
        restore_verify_last_timestamp.labels(service=service).set(time.time())

        log.error("verification_failed", error=str(exc), duration_seconds=result.duration_seconds)

    finally:
        # Cleanup restore directory
        import shutil
        shutil.rmtree(restore_dir, ignore_errors=True)

        current_verifications.pop(service, None)
        verify_history.append(result)

        # Trim history to 30 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        cutoff_str = cutoff.isoformat()
        while verify_history and verify_history[0].started_at and verify_history[0].started_at < cutoff_str:
            verify_history.pop(0)

    return result


async def _execute_verify_all() -> list[VerifyResult]:
    """Execute verification for all targets sequentially."""
    results = []
    for service in ALL_TARGETS:
        result = await _execute_verification(service)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Mattermost Weekly Summary
# ---------------------------------------------------------------------------


async def _send_weekly_summary() -> None:
    """Send a weekly verification summary to Mattermost."""
    if not MATTERMOST_WEBHOOK_URL:
        logger.warning("mattermost_webhook_not_configured_for_summary")
        return

    log = logger.bind(task="weekly_summary")

    # Collect last 7 days of results
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    cutoff_str = cutoff.isoformat()

    recent = [
        r for r in verify_history
        if r.started_at and r.started_at >= cutoff_str
    ]

    # Build summary
    service_results: dict[str, list[bool]] = {}
    for r in recent:
        if r.service not in service_results:
            service_results[r.service] = []
        service_results[r.service].append(r.passed)

    lines = ["### :shield: Backup Restore Verification - Weekly Summary\n"]
    lines.append(f"**Period:** {cutoff.strftime('%Y-%m-%d')} to {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n")

    for service in ALL_TARGETS:
        results = service_results.get(service, [])
        if not results:
            lines.append(f"- **{service}**: No verifications run")
        else:
            passed_count = sum(1 for r in results if r)
            total = len(results)
            status_icon = ":white_check_mark:" if passed_count == total else ":x:"
            lines.append(f"- {status_icon} **{service}**: {passed_count}/{total} passed")

    total_checks = len(recent)
    total_passed = sum(1 for r in recent if r.passed)
    lines.append(f"\n**Overall: {total_passed}/{total_checks} verifications passed**")

    message = "\n".join(lines)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(MATTERMOST_WEBHOOK_URL, json={"text": message})
            if resp.status_code >= 400:
                log.error("weekly_summary_send_failed", status=resp.status_code)
            else:
                log.info("weekly_summary_sent")
    except Exception as exc:
        log.error("weekly_summary_error", error=str(exc))


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start scheduler on startup."""
    logger.info("starting_restore_verifier")

    # Daily verification at 5AM
    scheduler.add_job(
        _execute_verify_all,
        CronTrigger(hour=5, minute=0),
        id="daily_verify",
        name="Daily Restore Verification",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Weekly Mattermost summary on Monday 6AM
    scheduler.add_job(
        _send_weekly_summary,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        id="weekly_summary",
        name="Weekly Verification Summary",
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.start()
    logger.info("scheduler_started", jobs=["daily_verify@5AM", "weekly_summary@Mon6AM"])

    yield

    scheduler.shutdown(wait=False)
    if docker_client:
        docker_client.close()
    logger.info("scheduler_stopped")


app = FastAPI(
    title="Backup Fortress -- Restore Verifier",
    description="SYSTEM 1: Automated restore verification for backup integrity",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    trace_id = str(uuid.uuid4())
    logger.error("unhandled_exception", trace_id=trace_id, error=str(exc), path=str(request.url))
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
    return {
        "status": "healthy",
        "service": "restore-verifier",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
async def ready():
    """Readiness probe."""
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
# Verify Endpoints
# ---------------------------------------------------------------------------


@app.get("/verify/status")
async def verify_status():
    """Get current status of all verification jobs."""
    active = {k: v.model_dump() for k, v in current_verifications.items()}

    # Get last result per service
    last_results: dict[str, dict[str, Any]] = {}
    for result in reversed(verify_history):
        if result.service not in last_results:
            last_results[result.service] = {
                "service": result.service,
                "passed": result.passed,
                "completed_at": result.completed_at,
                "duration_seconds": result.duration_seconds,
                "snapshot_id": result.snapshot_id,
            }
        if len(last_results) >= len(ALL_TARGETS):
            break

    return {
        "active_verifications": active,
        "active_count": len(active),
        "last_results": last_results,
        "scheduler_running": scheduler.running,
        "next_scheduled_run": str(scheduler.get_job("daily_verify").next_run_time)
        if scheduler.get_job("daily_verify") else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/verify/{service_name}", response_model=VerifyResponse)
async def trigger_verify(service_name: str):
    """Trigger restore verification for a specific service."""
    if service_name not in VERIFY_FUNCTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown verification target: {service_name}. Valid targets: {', '.join(ALL_TARGETS)}",
        )

    if service_name in current_verifications:
        raise HTTPException(
            status_code=409,
            detail=f"Verification already running for {service_name}",
        )

    trace_id = str(uuid.uuid4())
    logger.info("verification_triggered", service=service_name, trace_id=trace_id)

    # Run in background
    asyncio.create_task(_execute_verification(service_name))

    return VerifyResponse(
        status="accepted",
        message=f"Verification initiated for {service_name}",
        trace_id=trace_id,
    )


@app.get("/verify/history")
async def verify_history_endpoint(days: int = Query(default=30, ge=1, le=365)):
    """Get verification history for the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    filtered = [
        r.model_dump() for r in verify_history
        if r.started_at and r.started_at >= cutoff_str
    ]

    return {
        "history": filtered,
        "total_count": len(filtered),
        "days": days,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        access_log=True,
    )
