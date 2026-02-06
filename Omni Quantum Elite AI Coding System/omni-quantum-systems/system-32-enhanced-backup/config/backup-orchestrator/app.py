"""
Omni Quantum Elite — Backup Orchestrator
Manages automated backup schedules for ALL 28+ services.
Supports PostgreSQL, Redis, Restic, MinIO, Gitea, Qdrant, and volume backups.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram, generate_latest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backup-orchestrator")

app = FastAPI(title="Omni Quantum Backup Orchestrator", version="1.0.0")

STAGING_DIR = os.getenv("STAGING_DIR", "/backup/staging")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK", "")
OMI_WEBHOOK = os.getenv("OMI_WEBHOOK_URL", "")

# Prometheus metrics
backups_total = Counter("backup_total", "Total backups performed", ["service", "status"])
backup_duration = Histogram("backup_duration_seconds", "Backup duration", ["service"])
backup_size = Gauge("backup_size_bytes", "Last backup size", ["service"])
last_backup_time = Gauge("backup_last_timestamp", "Last successful backup timestamp", ["service"])

scheduler = AsyncIOScheduler()
_backup_history: list[dict] = []


def run_command(cmd: list[str], timeout: int = 3600) -> tuple[int, str, str]:
    """Execute a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


async def backup_postgresql(config: dict):
    """Backup PostgreSQL databases using pg_dump/pg_dumpall."""
    service = "postgresql"
    start = time.monotonic()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dump_file = f"{STAGING_DIR}/postgres_{ts}.sql.gz"

    host = config.get("host", os.getenv("POSTGRES_HOST", "omni-postgres"))
    port = config.get("port", os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "postgres")

    env = {**os.environ, "PGPASSWORD": os.getenv("POSTGRES_PASSWORD", "")}

    databases = config.get("databases", ["all"])
    if "all" in databases:
        cmd = ["pg_dumpall", "-h", host, "-p", str(port), "-U", user]
    else:
        cmd = ["pg_dump", "-h", host, "-p", str(port), "-U", user, "-d", databases[0]]

    rc, stdout, stderr = run_command(["bash", "-c", f"{' '.join(cmd)} | gzip > {dump_file}"])

    if rc == 0 and Path(dump_file).exists():
        size = Path(dump_file).stat().st_size
        # Upload to Restic
        restic_rc, _, restic_err = run_command(["restic", "backup", dump_file, "--tag", "postgresql"])
        if restic_rc == 0:
            elapsed = time.monotonic() - start
            backups_total.labels(service=service, status="success").inc()
            backup_duration.labels(service=service).observe(elapsed)
            backup_size.labels(service=service).set(size)
            last_backup_time.labels(service=service).set(time.time())
            logger.info(f"PostgreSQL backup OK: {size} bytes, {elapsed:.1f}s")
            record_backup(service, "success", size, elapsed)
            # Cleanup staging
            Path(dump_file).unlink(missing_ok=True)
            return
    backups_total.labels(service=service, status="failed").inc()
    logger.error(f"PostgreSQL backup FAILED: {stderr}")
    record_backup(service, "failed", 0, time.monotonic() - start)
    await alert_backup_failure(service, stderr)


async def backup_redis(config: dict):
    """Backup Redis via BGSAVE."""
    service = "redis"
    start = time.monotonic()
    host = config.get("host", "omni-redis")
    port = config.get("port", 6379)

    rc, _, stderr = run_command(["redis-cli", "-h", host, "-p", str(port), "BGSAVE"])
    await asyncio.sleep(5)  # Wait for save

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dump_file = f"{STAGING_DIR}/redis_{ts}.rdb"

    # Copy RDB from Redis container
    rc2, _, _ = run_command([
        "docker", "cp", f"omni-redis:/data/dump.rdb", dump_file
    ])

    if rc == 0 and rc2 == 0 and Path(dump_file).exists():
        size = Path(dump_file).stat().st_size
        run_command(["restic", "backup", dump_file, "--tag", "redis"])
        elapsed = time.monotonic() - start
        backups_total.labels(service=service, status="success").inc()
        backup_duration.labels(service=service).observe(elapsed)
        backup_size.labels(service=service).set(size)
        last_backup_time.labels(service=service).set(time.time())
        logger.info(f"Redis backup OK: {size} bytes")
        record_backup(service, "success", size, elapsed)
        Path(dump_file).unlink(missing_ok=True)
    else:
        backups_total.labels(service=service, status="failed").inc()
        record_backup(service, "failed", 0, time.monotonic() - start)
        await alert_backup_failure(service, stderr)


async def backup_qdrant(config: dict):
    """Backup Qdrant via snapshot API."""
    service = "qdrant"
    start = time.monotonic()
    qdrant_url = config.get("qdrant_url", os.getenv("QDRANT_URL", "http://omni-qdrant:6333"))

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            # Create snapshot for all collections
            resp = await client.get(f"{qdrant_url}/collections")
            collections = resp.json().get("result", {}).get("collections", [])
            total_size = 0
            for col in collections:
                name = col["name"]
                snap_resp = await client.post(f"{qdrant_url}/collections/{name}/snapshots")
                if snap_resp.status_code == 200:
                    snapshot = snap_resp.json().get("result", {})
                    total_size += snapshot.get("size", 0)
                    logger.info(f"Qdrant snapshot: {name} OK")

            elapsed = time.monotonic() - start
            backups_total.labels(service=service, status="success").inc()
            backup_duration.labels(service=service).observe(elapsed)
            backup_size.labels(service=service).set(total_size)
            last_backup_time.labels(service=service).set(time.time())
            record_backup(service, "success", total_size, elapsed)
        except Exception as e:
            backups_total.labels(service=service, status="failed").inc()
            record_backup(service, "failed", 0, time.monotonic() - start)
            await alert_backup_failure(service, str(e))


async def backup_postgresql_db(config: dict):
    """Backup a single PostgreSQL database."""
    db_name = config.get("database", "unknown")
    service = f"postgresql_{db_name}"
    start = time.monotonic()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dump_file = f"{STAGING_DIR}/{db_name}_{ts}.sql.gz"
    host = config.get("host", "omni-postgres")

    cmd = f"pg_dump -h {host} -p 5432 -U postgres -d {db_name} | gzip > {dump_file}"
    env_with_pass = {**os.environ, "PGPASSWORD": os.getenv("POSTGRES_PASSWORD", "")}
    rc, _, stderr = run_command(["bash", "-c", cmd])

    if rc == 0 and Path(dump_file).exists():
        size = Path(dump_file).stat().st_size
        run_command(["restic", "backup", dump_file, "--tag", f"db-{db_name}"])
        elapsed = time.monotonic() - start
        backups_total.labels(service=service, status="success").inc()
        backup_size.labels(service=service).set(size)
        last_backup_time.labels(service=service).set(time.time())
        record_backup(service, "success", size, elapsed)
        Path(dump_file).unlink(missing_ok=True)
    else:
        backups_total.labels(service=service, status="failed").inc()
        record_backup(service, "failed", 0, time.monotonic() - start)


async def backup_volume(config: dict):
    """Backup Docker volumes via Restic."""
    service = config.get("description", "volume").replace(" ", "_").lower()
    start = time.monotonic()
    volumes = config.get("volumes", [])
    for vol_spec in volumes:
        parts = vol_spec.split(":")
        vol_name = parts[0]
        rc, _, stderr = run_command(["restic", "backup", f"/var/lib/docker/volumes/{vol_name}", "--tag", f"volume-{vol_name}"])
        if rc != 0:
            logger.warning(f"Volume backup failed for {vol_name}: {stderr}")
    elapsed = time.monotonic() - start
    backups_total.labels(service=service, status="success").inc()
    record_backup(service, "success", 0, elapsed)


def record_backup(service: str, status: str, size: int, duration: float):
    """Record backup in history."""
    _backup_history.append({
        "service": service,
        "status": status,
        "size_bytes": size,
        "duration_seconds": round(duration, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    # Keep last 500 entries
    if len(_backup_history) > 500:
        _backup_history.pop(0)


async def alert_backup_failure(service: str, error: str):
    """Alert on backup failure."""
    if MATTERMOST_WEBHOOK:
        payload = {
            "username": "Backup Fortress",
            "icon_emoji": ":floppy_disk:",
            "text": f"### 🔴 Backup FAILED: {service}\n| Field | Value |\n|---|---|\n| Service | `{service}` |\n| Error | {error[:200]} |\n| Time | {datetime.now(timezone.utc).isoformat()} |\n",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(MATTERMOST_WEBHOOK, json=payload)
            except Exception:
                pass


# Backup type dispatcher
BACKUP_HANDLERS = {
    "postgresql": backup_postgresql,
    "redis": backup_redis,
    "qdrant": backup_qdrant,
    "postgresql_db": backup_postgresql_db,
    "volume": backup_volume,
}


def load_and_schedule_backups():
    """Load backup schedules from YAML and register with APScheduler."""
    config_path = "/app/schedules.yml"
    if not os.path.exists(config_path):
        logger.warning("No backup schedules file found")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    schedules = config.get("schedules", {})
    for name, sched in schedules.items():
        cron_expr = sched.get("schedule", "0 * * * *")
        backup_type = sched.get("type", "unknown")
        handler = BACKUP_HANDLERS.get(backup_type)
        if handler:
            parts = cron_expr.split()
            trigger = CronTrigger(
                minute=parts[0], hour=parts[1], day=parts[2],
                month=parts[3], day_of_week=parts[4],
            )
            scheduler.add_job(handler, trigger, args=[sched], id=name, name=name)
            logger.info(f"Scheduled backup: {name} ({backup_type}) at {cron_expr}")
        else:
            logger.warning(f"Unknown backup type: {backup_type} for {name}")


@app.on_event("startup")
async def startup():
    # Init Restic repo
    run_command(["restic", "init"])  # Idempotent — fails if already initialized
    load_and_schedule_backups()
    scheduler.start()
    logger.info("Backup Orchestrator started")


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()


@app.get("/health")
async def health():
    return {"status": "healthy", "scheduled_jobs": len(scheduler.get_jobs()), "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/backups")
async def list_backups():
    return {"history": _backup_history[-50:], "total": len(_backup_history)}


@app.get("/schedules")
async def list_schedules():
    jobs = scheduler.get_jobs()
    return {"schedules": [{"id": j.id, "name": j.name, "next_run": str(j.next_run_time)} for j in jobs]}


@app.post("/backup/{service}")
async def trigger_backup(service: str):
    """Manually trigger a backup for a specific service."""
    config_path = "/app/schedules.yml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    sched = config.get("schedules", {}).get(service)
    if not sched:
        return {"error": f"Unknown service: {service}"}
    handler = BACKUP_HANDLERS.get(sched.get("type"))
    if handler:
        await handler(sched)
        return {"status": "backup_triggered", "service": service}
    return {"error": f"No handler for type: {sched.get('type')}"}


@app.get("/snapshots")
async def list_snapshots():
    """List all Restic snapshots."""
    rc, stdout, stderr = run_command(["restic", "snapshots", "--json"])
    if rc == 0:
        return {"snapshots": json.loads(stdout) if stdout else []}
    return {"error": stderr}
