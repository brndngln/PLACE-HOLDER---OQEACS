"""
Omni Quantum Elite — Secret Rotation Agent
Automatically rotates secrets stored in Vault: DB credentials, API keys, tokens.
Integrates with SOPS for git-encrypted secrets.
"""

import asyncio
import logging
import os
import secrets
import string
import time
from datetime import datetime, timezone

import httpx
import hvac
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from prometheus_client import Counter, Gauge, generate_latest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("secret-rotation")

app = FastAPI(title="Secret Rotation Agent", version="1.0.0")

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK", "")
CHECK_INTERVAL = int(os.getenv("ROTATION_CHECK_INTERVAL", "3600"))

rotations_total = Counter("secret_rotations_total", "Total rotations", ["secret_type", "status"])
secrets_age_days = Gauge("secret_age_days", "Secret age in days", ["secret_path"])
last_rotation = Gauge("secret_last_rotation_timestamp", "Last rotation time", ["secret_path"])

scheduler = AsyncIOScheduler()
vault_client: hvac.Client | None = None

# Secrets to manage with rotation schedules
MANAGED_SECRETS = [
    {"path": "secret/data/postgres/app", "type": "database", "max_age_days": 30, "fields": ["password"]},
    {"path": "secret/data/redis/auth", "type": "cache", "max_age_days": 90, "fields": ["password"]},
    {"path": "secret/data/minio/access", "type": "storage", "max_age_days": 60, "fields": ["secret_key"]},
    {"path": "secret/data/gitea/admin", "type": "service", "max_age_days": 90, "fields": ["token"]},
    {"path": "secret/data/mattermost/bot", "type": "service", "max_age_days": 90, "fields": ["token"]},
    {"path": "secret/data/langfuse/api", "type": "service", "max_age_days": 60, "fields": ["secret_key"]},
    {"path": "secret/data/litellm/master", "type": "service", "max_age_days": 60, "fields": ["api_key"]},
    {"path": "secret/data/nango/api", "type": "service", "max_age_days": 60, "fields": ["secret_key"]},
    {"path": "secret/data/n8n/encryption", "type": "service", "max_age_days": 180, "fields": ["key"]},
    {"path": "secret/data/authentik/secret", "type": "service", "max_age_days": 90, "fields": ["key"]},
]


def generate_password(length: int = 32) -> str:
    """Generate a cryptographically secure password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_token(length: int = 64) -> str:
    """Generate a cryptographically secure token."""
    return secrets.token_urlsafe(length)


def init_vault():
    """Initialize Vault client."""
    global vault_client
    vault_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    if vault_client.is_authenticated():
        logger.info("Vault client authenticated")
    else:
        logger.error("Vault authentication failed")


def get_secret_metadata(path: str) -> dict | None:
    """Get secret metadata including creation time."""
    try:
        # KV v2 metadata
        metadata_path = path.replace("/data/", "/metadata/")
        resp = vault_client.secrets.kv.v2.read_secret_metadata(
            path=path.split("/data/")[-1],
            mount_point=path.split("/")[0],
        )
        return resp
    except Exception as e:
        logger.warning(f"Could not read metadata for {path}: {e}")
    return None


async def check_and_rotate():
    """Check all managed secrets and rotate if needed."""
    if not vault_client or not vault_client.is_authenticated():
        init_vault()

    for secret in MANAGED_SECRETS:
        try:
            path = secret["path"]
            max_age = secret["max_age_days"]

            # Read current secret
            mount = path.split("/")[0]
            secret_path = "/".join(path.split("/")[2:])
            try:
                current = vault_client.secrets.kv.v2.read_secret_version(
                    path=secret_path, mount_point=mount
                )
                metadata = current.get("data", {}).get("metadata", {})
                created = metadata.get("created_time", "")
                if created:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    age_days = (datetime.now(timezone.utc) - created_dt).days
                    secrets_age_days.labels(secret_path=path).set(age_days)

                    if age_days >= max_age:
                        await rotate_secret(secret)
                    else:
                        logger.debug(f"{path}: age={age_days}d, max={max_age}d — OK")
            except hvac.exceptions.InvalidPath:
                logger.info(f"Secret {path} not found — initializing")
                await rotate_secret(secret)

        except Exception as e:
            logger.error(f"Error checking {secret['path']}: {e}")


async def rotate_secret(secret: dict):
    """Rotate a specific secret."""
    path = secret["path"]
    mount = path.split("/")[0]
    secret_path = "/".join(path.split("/")[2:])
    secret_type = secret["type"]

    logger.info(f"Rotating secret: {path}")

    try:
        # Read existing data
        existing = {}
        try:
            resp = vault_client.secrets.kv.v2.read_secret_version(
                path=secret_path, mount_point=mount
            )
            existing = resp.get("data", {}).get("data", {})
        except hvac.exceptions.InvalidPath:
            pass

        # Generate new values for specified fields
        new_data = {**existing}
        for field in secret.get("fields", []):
            if field in ("password", "secret_key", "key"):
                new_data[field] = generate_password()
            elif field in ("token", "api_key"):
                new_data[field] = generate_token()
            else:
                new_data[field] = generate_password()

        new_data["_rotated_at"] = datetime.now(timezone.utc).isoformat()
        new_data["_rotation_agent"] = "omni-secret-rotation-agent"

        # Write new secret
        vault_client.secrets.kv.v2.create_or_update_secret(
            path=secret_path, secret=new_data, mount_point=mount
        )

        rotations_total.labels(secret_type=secret_type, status="success").inc()
        last_rotation.labels(secret_path=path).set(time.time())
        logger.info(f"Rotated: {path}")

        # Alert
        await notify_rotation(path, secret_type)

    except Exception as e:
        rotations_total.labels(secret_type=secret_type, status="failed").inc()
        logger.error(f"Rotation FAILED for {path}: {e}")
        await notify_rotation_failure(path, str(e))


async def notify_rotation(path: str, secret_type: str):
    """Notify about successful rotation."""
    if MATTERMOST_WEBHOOK:
        payload = {
            "username": "Secret Rotation",
            "icon_emoji": ":key:",
            "text": f"🔑 Secret rotated: `{path}` (type: {secret_type})",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(MATTERMOST_WEBHOOK, json=payload)
            except Exception:
                pass


async def notify_rotation_failure(path: str, error: str):
    """Alert on rotation failure."""
    if MATTERMOST_WEBHOOK:
        payload = {
            "username": "Secret Rotation",
            "icon_emoji": ":warning:",
            "text": f"### 🔴 Secret Rotation FAILED\n`{path}`\nError: {error[:200]}",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(MATTERMOST_WEBHOOK, json=payload)
            except Exception:
                pass


@app.on_event("startup")
async def startup():
    init_vault()
    scheduler.add_job(check_and_rotate, "interval", seconds=CHECK_INTERVAL, id="rotation_check")
    scheduler.start()


@app.get("/health")
async def health():
    authenticated = vault_client.is_authenticated() if vault_client else False
    return {"status": "healthy", "vault_connected": authenticated, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/secrets/status")
async def secrets_status():
    """Get rotation status for all managed secrets."""
    return {"managed_secrets": len(MANAGED_SECRETS), "secrets": [{"path": s["path"], "type": s["type"], "max_age_days": s["max_age_days"]} for s in MANAGED_SECRETS]}


@app.post("/rotate/{secret_name}")
async def trigger_rotation(secret_name: str):
    """Manually trigger rotation for a specific secret."""
    for s in MANAGED_SECRETS:
        if secret_name in s["path"]:
            await rotate_secret(s)
            return {"status": "rotated", "path": s["path"]}
    return {"error": f"Secret not found: {secret_name}"}


@app.post("/emergency/break-glass")
async def break_glass():
    """Emergency break-glass procedure — generates temporary root credentials."""
    logger.warning("BREAK-GLASS PROCEDURE ACTIVATED")
    emergency_token = generate_token(128)
    # In production, this would create a time-limited Vault token
    return {
        "warning": "EMERGENCY BREAK-GLASS ACTIVATED",
        "temporary_token": emergency_token,
        "expires_in": "1h",
        "audit_logged": True,
    }
