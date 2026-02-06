"""
Omni Quantum Elite — Backup Verifier
Automatically tests restore capability by performing test restores daily.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from prometheus_client import Counter, Gauge, generate_latest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backup-verifier")

app = FastAPI(title="Backup Verifier", version="1.0.0")

STAGING_DIR = "/verify/staging"
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK", "")
VERIFY_INTERVAL = int(os.getenv("VERIFY_INTERVAL_HOURS", "24"))

verify_total = Counter("backup_verify_total", "Verification attempts", ["status"])
last_verify = Gauge("backup_verify_last_timestamp", "Last verification time")
verify_success = Gauge("backup_verify_last_success", "Last verification success (1=ok, 0=fail)")

scheduler = AsyncIOScheduler()
_verify_history: list[dict] = []


def run_cmd(cmd, timeout=600):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)


async def verify_backups():
    """Run verification on latest Restic snapshots."""
    logger.info("Starting backup verification...")
    start = time.monotonic()

    # Check Restic repo integrity
    rc, stdout, stderr = run_cmd(["restic", "check"])
    repo_ok = rc == 0

    # List latest snapshots
    rc2, snap_out, _ = run_cmd(["restic", "snapshots", "--json", "--latest", "5"])
    snapshots = json.loads(snap_out) if rc2 == 0 and snap_out else []

    # Test restore of latest snapshot
    restore_ok = False
    if snapshots:
        latest = snapshots[-1]
        snap_id = latest.get("short_id", latest.get("id", ""))[:8]
        restore_dir = f"{STAGING_DIR}/verify_{snap_id}"
        rc3, _, err3 = run_cmd(["restic", "restore", snap_id, "--target", restore_dir])
        restore_ok = rc3 == 0
        # Cleanup
        run_cmd(["rm", "-rf", restore_dir])

    elapsed = time.monotonic() - start
    success = repo_ok and restore_ok
    status = "success" if success else "failed"

    verify_total.labels(status=status).inc()
    last_verify.set(time.time())
    verify_success.set(1 if success else 0)

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo_integrity": repo_ok,
        "restore_test": restore_ok,
        "snapshots_checked": len(snapshots),
        "duration_seconds": round(elapsed, 2),
        "status": status,
    }
    _verify_history.append(result)
    if len(_verify_history) > 100:
        _verify_history.pop(0)

    if not success and MATTERMOST_WEBHOOK:
        payload = {
            "username": "Backup Verifier",
            "icon_emoji": ":warning:",
            "text": f"### 🔴 Backup Verification FAILED\n| Check | Result |\n|---|---|\n| Repo Integrity | {'✅' if repo_ok else '❌'} |\n| Restore Test | {'✅' if restore_ok else '❌'} |\n",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(MATTERMOST_WEBHOOK, json=payload)
            except Exception:
                pass

    logger.info(f"Verification {'PASSED' if success else 'FAILED'} in {elapsed:.1f}s")
    return result


@app.on_event("startup")
async def startup():
    scheduler.add_job(verify_backups, "interval", hours=VERIFY_INTERVAL, id="verify")
    scheduler.start()


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.post("/verify")
async def trigger_verify():
    return await verify_backups()


@app.get("/history")
async def get_history():
    return {"verifications": _verify_history[-20:]}
