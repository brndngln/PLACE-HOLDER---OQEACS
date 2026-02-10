#!/usr/bin/env python3
"""
SYSTEM 33 — CRYPTOGRAPHIC FORTRESS PRO: Enhanced Secret Rotation Agent
Omni Quantum Elite AI Coding System — Security & Identity Layer

Automated secret rotation with:
- Cryptographically secure secret generation
- Vault KV v2 versioned storage
- Service restart/reload with health verification
- Automatic rollback on failure
- Prometheus metrics
- Mattermost notifications (immediate for failures, daily digest for success)
"""

import hashlib
import os
import secrets
import string
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
import hvac
import yaml
from prometheus_client import CollectorRegistry, Counter, Gauge, push_to_gateway

# ───────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")
VAULT_MOUNT = os.getenv("VAULT_MOUNT", "secret")
SCHEDULE_FILE = os.getenv("SCHEDULE_FILE", "/opt/cryptographic-fortress/config/rotation-schedules.yaml")
PROMETHEUS_PUSHGATEWAY = os.getenv("PROMETHEUS_PUSHGATEWAY", "http://omni-prometheus:9091")
MATTERMOST_WEBHOOK_URL = os.getenv("MATTERMOST_WEBHOOK_URL", "")
MATTERMOST_CHANNEL = os.getenv("MATTERMOST_CHANNEL", "#security-alerts")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
DOCKER_SOCKET = os.getenv("DOCKER_SOCKET", "unix:///var/run/docker.sock")

# ───────────────────────────────────────────────────────────────────────
# Prometheus Metrics
# ───────────────────────────────────────────────────────────────────────

registry = CollectorRegistry()

rotation_last_success = Gauge(
    "secret_rotation_last_success",
    "Unix timestamp of last successful rotation",
    ["service", "secret"],
    registry=registry,
)

rotation_failures_total = Counter(
    "secret_rotation_failures_total",
    "Total number of rotation failures",
    ["service", "secret"],
    registry=registry,
)

rotation_next_timestamp = Gauge(
    "secret_next_rotation_timestamp",
    "Unix timestamp of next scheduled rotation",
    ["service", "secret"],
    registry=registry,
)

rotation_duration_seconds = Gauge(
    "secret_rotation_duration_seconds",
    "Duration of last rotation attempt in seconds",
    ["service", "secret"],
    registry=registry,
)


# ───────────────────────────────────────────────────────────────────────
# Types
# ───────────────────────────────────────────────────────────────────────


class RotationStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLBACK = "rollback"


@dataclass
class RotationResult:
    secret_name: str
    service: str
    status: RotationStatus
    vault_path: str
    old_version: int = 0
    new_version: int = 0
    duration_seconds: float = 0.0
    error: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ───────────────────────────────────────────────────────────────────────
# Secret Generation
# ───────────────────────────────────────────────────────────────────────

CHARSETS = {
    "alphanumeric": string.ascii_letters + string.digits,
    "alphanumeric_special": string.ascii_letters + string.digits + "!@#$%^&*()-_=+",
    "hex": string.hexdigits.lower(),
    "numeric": string.digits,
    "base64": string.ascii_letters + string.digits + "+/=",
}


def generate_secret(
    secret_type: str,
    length: int = 32,
    charset: str = "alphanumeric",
) -> str:
    """Generate a cryptographically random secret value."""
    if secret_type == "hex_token":
        return secrets.token_hex(length // 2)
    if secret_type == "token" or secret_type == "password":
        alphabet = CHARSETS.get(charset, CHARSETS["alphanumeric"])
        return "".join(secrets.choice(alphabet) for _ in range(length))
    if secret_type == "access_key_pair":
        # Returns just one key; caller generates both
        alphabet = CHARSETS.get(charset, CHARSETS["alphanumeric"])
        return "".join(secrets.choice(alphabet) for _ in range(length))
    # Default: alphanumeric
    return "".join(secrets.choice(CHARSETS["alphanumeric"]) for _ in range(length))


# ───────────────────────────────────────────────────────────────────────
# Vault Operations
# ───────────────────────────────────────────────────────────────────────


def get_vault_client() -> hvac.Client:
    """Create authenticated Vault client."""
    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    if not client.is_authenticated():
        raise RuntimeError("Vault authentication failed")
    return client


def read_secret_version(vault: hvac.Client, path: str) -> tuple[dict, int]:
    """Read current secret and return (data, version)."""
    try:
        result = vault.secrets.kv.v2.read_secret_version(
            path=path, mount_point=VAULT_MOUNT, raise_on_deleted_version=True
        )
        data = result["data"]["data"]
        version = result["data"]["metadata"]["version"]
        return data, version
    except hvac.exceptions.InvalidPath:
        return {}, 0


def write_secret(vault: hvac.Client, path: str, data: dict) -> int:
    """Write a new secret version, return new version number."""
    result = vault.secrets.kv.v2.create_or_update_secret(
        path=path, secret=data, mount_point=VAULT_MOUNT
    )
    return result["data"]["version"]


def rollback_secret(vault: hvac.Client, path: str, version: int) -> None:
    """Rollback to a previous secret version by re-writing it."""
    old_data = vault.secrets.kv.v2.read_secret_version(
        path=path, version=version, mount_point=VAULT_MOUNT
    )
    vault.secrets.kv.v2.create_or_update_secret(
        path=path,
        secret=old_data["data"]["data"],
        mount_point=VAULT_MOUNT,
    )


def get_last_rotation_time(vault: hvac.Client, path: str) -> datetime | None:
    """Get the timestamp of the last secret version (= last rotation)."""
    try:
        result = vault.secrets.kv.v2.read_secret_version(
            path=path, mount_point=VAULT_MOUNT
        )
        ts_str = result["data"]["metadata"]["created_time"]
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return None


# ───────────────────────────────────────────────────────────────────────
# Service Restart / Reload
# ───────────────────────────────────────────────────────────────────────


def restart_service(service_name: str, method: str) -> bool:
    """Restart or reload a service after secret rotation."""
    if DRY_RUN:
        print(f"    [DRY RUN] Would restart {service_name} via {method}")
        return True

    if method == "docker_restart":
        return docker_restart(service_name)
    elif method == "env_reload":
        # Some services support SIGHUP or config reload
        return docker_signal(service_name, "SIGHUP")
    elif method == "redis_config_set":
        return redis_config_set(service_name)
    elif method == "api_update":
        # API-based updates don't need restart
        return True
    elif method == "none":
        return True
    elif method == "minio_rotate_credentials":
        return docker_restart(service_name)
    elif method == "crowdsec_bouncer_rotate":
        return docker_restart(service_name)
    elif method == "authentik_provider_update":
        return True  # Updated via Authentik API
    else:
        print(f"    WARNING: Unknown restart method '{method}', defaulting to docker_restart")
        return docker_restart(service_name)


def docker_restart(container_name: str) -> bool:
    """Restart a Docker container."""
    try:
        result = subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True, text=True, timeout=60,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    Docker restart failed: {e}")
        return False


def docker_signal(container_name: str, signal: str) -> bool:
    """Send a signal to a Docker container."""
    try:
        result = subprocess.run(
            ["docker", "kill", f"--signal={signal}", container_name],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    Docker signal failed: {e}")
        return False


def redis_config_set(container_name: str) -> bool:
    """Update Redis password via CONFIG SET (no restart needed)."""
    # The new password is already in Vault; we'd need to read it
    # For now, fall back to restart
    return docker_restart(container_name)


# ───────────────────────────────────────────────────────────────────────
# Health Check
# ───────────────────────────────────────────────────────────────────────


def check_health(health_cmd: str, timeout: int = 30, retries: int = 3) -> bool:
    """Run a health check command, retrying on failure."""
    if not health_cmd or DRY_RUN:
        return True

    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                ["sh", "-c", health_cmd],
                capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

        if attempt < retries:
            time.sleep(5 * attempt)

    return False


# ───────────────────────────────────────────────────────────────────────
# Rotation Logic
# ───────────────────────────────────────────────────────────────────────


def should_rotate(
    vault: hvac.Client,
    secret_config: dict,
    interval_days: int,
) -> bool:
    """Check if a secret is due for rotation."""
    path = secret_config["vault_path"]
    last_rotated = get_last_rotation_time(vault, path)
    if last_rotated is None:
        return True  # Never rotated

    age_days = (datetime.now(timezone.utc) - last_rotated).total_seconds() / 86400
    return age_days >= interval_days


def rotate_secret(
    vault: hvac.Client,
    secret_config: dict,
    global_config: dict,
) -> RotationResult:
    """Rotate a single secret through the full lifecycle."""
    name = secret_config["name"]
    path = secret_config["vault_path"]
    vault_key = secret_config.get("vault_key", "value")
    service = secret_config.get("service", "unknown")
    restart_method = secret_config.get("restart_method", "docker_restart")
    health_cmd = secret_config.get("health_check", "")
    secret_type = secret_config.get("type", "password")
    length = secret_config.get("length", 32)
    charset = secret_config.get("charset", "alphanumeric")

    start_time = time.time()
    print(f"\n  Rotating: {name} (path: {path})")

    # Skip external/manual secrets
    if secret_type == "external" or secret_config.get("rotation_method") == "manual":
        print(f"    Skipped — external/manual rotation required")
        return RotationResult(
            secret_name=name, service=service,
            status=RotationStatus.SKIPPED, vault_path=path,
        )

    try:
        # Step 1: Read current secret version
        current_data, current_version = read_secret_version(vault, path)
        print(f"    Current version: {current_version}")

        # Step 2: Generate new secret value(s)
        new_data = dict(current_data)
        keys = [k.strip() for k in vault_key.split(",")]

        for key in keys:
            if secret_type == "access_key_pair" and "access_key" in key:
                new_data[key] = generate_secret("token", secret_config.get("access_key_length", 20), charset)
            elif secret_type == "access_key_pair" and "secret_key" in key:
                new_data[key] = generate_secret("token", secret_config.get("secret_key_length", 40), charset)
            else:
                new_data[key] = generate_secret(secret_type, length, charset)

        # Add rotation metadata
        new_data["_rotated_at"] = datetime.now(timezone.utc).isoformat()
        new_data["_rotated_by"] = "cryptographic-fortress-pro"
        new_data["_previous_version"] = current_version

        if DRY_RUN:
            print(f"    [DRY RUN] Would write new version of {path}")
            duration = time.time() - start_time
            return RotationResult(
                secret_name=name, service=service,
                status=RotationStatus.SUCCESS, vault_path=path,
                old_version=current_version, new_version=current_version + 1,
                duration_seconds=duration,
            )

        # Step 3: Write new secret to Vault
        new_version = write_secret(vault, path, new_data)
        print(f"    New version: {new_version}")

        # Step 4: Restart/reload service
        print(f"    Restarting {service} (method: {restart_method})")
        restart_ok = restart_service(service, restart_method)
        if not restart_ok:
            print(f"    WARNING: Service restart failed for {service}")

        # Wait for service to come up
        time.sleep(5)

        # Restart dependent services
        for dep in secret_config.get("dependent_services", []):
            print(f"    Restarting dependent: {dep}")
            restart_service(dep, "docker_restart")
            time.sleep(3)

        # Step 5: Health check
        print(f"    Running health check ...")
        timeout = global_config.get("health_check_timeout", 30)
        retries = global_config.get("health_check_retries", 3)
        healthy = check_health(health_cmd, timeout=timeout, retries=retries)

        if not healthy and global_config.get("rollback_on_failure", True):
            # Step 6a: Rollback
            print(f"    HEALTH CHECK FAILED — rolling back to version {current_version}")
            rollback_secret(vault, path, current_version)
            restart_service(service, restart_method)
            time.sleep(5)

            for dep in secret_config.get("dependent_services", []):
                restart_service(dep, "docker_restart")

            duration = time.time() - start_time
            rotation_failures_total.labels(service=service, secret=name).inc()
            return RotationResult(
                secret_name=name, service=service,
                status=RotationStatus.ROLLBACK, vault_path=path,
                old_version=current_version, new_version=new_version,
                duration_seconds=duration,
                error="Health check failed after rotation — rolled back",
            )

        # Step 6b: Success
        duration = time.time() - start_time
        rotation_last_success.labels(service=service, secret=name).set(time.time())
        rotation_duration_seconds.labels(service=service, secret=name).set(duration)
        print(f"    Rotation successful ({duration:.1f}s)")

        return RotationResult(
            secret_name=name, service=service,
            status=RotationStatus.SUCCESS, vault_path=path,
            old_version=current_version, new_version=new_version,
            duration_seconds=duration,
        )

    except Exception as e:
        duration = time.time() - start_time
        rotation_failures_total.labels(service=service, secret=name).inc()
        print(f"    ERROR: {e}")
        return RotationResult(
            secret_name=name, service=service,
            status=RotationStatus.FAILED, vault_path=path,
            duration_seconds=duration,
            error=str(e),
        )


# ───────────────────────────────────────────────────────────────────────
# Notifications
# ───────────────────────────────────────────────────────────────────────


def send_mattermost_notification(
    results: list[RotationResult],
    is_digest: bool = False,
) -> None:
    """Send rotation results to Mattermost."""
    if not MATTERMOST_WEBHOOK_URL:
        return

    successes = [r for r in results if r.status == RotationStatus.SUCCESS]
    failures = [r for r in results if r.status in (RotationStatus.FAILED, RotationStatus.ROLLBACK)]
    skipped = [r for r in results if r.status == RotationStatus.SKIPPED]

    if is_digest and not results:
        return

    lines: list[str] = []

    if is_digest:
        lines.append("### Secret Rotation Daily Digest")
        lines.append(f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
        lines.append(f"**Rotated:** {len(successes)} | **Failed:** {len(failures)} | **Skipped:** {len(skipped)}")
        lines.append("")

        if successes:
            lines.append("#### Successful Rotations")
            for r in successes:
                lines.append(f"- `{r.secret_name}` ({r.service}) v{r.old_version} -> v{r.new_version} ({r.duration_seconds:.1f}s)")

    if failures:
        lines.append("#### FAILED Rotations")
        for r in failures:
            status = "ROLLED BACK" if r.status == RotationStatus.ROLLBACK else "FAILED"
            lines.append(f"- **{status}** `{r.secret_name}` ({r.service}): {r.error}")

    if not lines:
        return

    payload = {
        "channel": MATTERMOST_CHANNEL,
        "username": "Cryptographic Fortress",
        "icon_emoji": ":lock:",
        "text": "\n".join(lines),
    }

    try:
        with httpx.Client(timeout=10) as client:
            client.post(MATTERMOST_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"WARNING: Mattermost notification failed: {e}")


def send_immediate_failure(result: RotationResult) -> None:
    """Send immediate alert for rotation failure."""
    send_mattermost_notification([result], is_digest=False)


# ───────────────────────────────────────────────────────────────────────
# Schedule Loading
# ───────────────────────────────────────────────────────────────────────


def load_schedule(path: str) -> dict:
    """Load rotation schedule from YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def get_all_secrets(schedule: dict) -> list[tuple[dict, int]]:
    """Extract all secrets with their rotation intervals."""
    all_secrets: list[tuple[dict, int]] = []

    for tier_key in ("high_sensitivity", "medium_sensitivity", "low_sensitivity"):
        tier = schedule.get(tier_key, {})
        interval = tier.get("rotation_interval_days", 90)
        for secret in tier.get("secrets", []):
            all_secrets.append((secret, interval))

    return all_secrets


# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────


def main() -> None:
    print("=" * 72)
    print("SYSTEM 33 — CRYPTOGRAPHIC FORTRESS PRO: Secret Rotation Agent")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    if DRY_RUN:
        print("MODE: DRY RUN — no changes will be made")
    print("=" * 72)

    # Load schedule
    schedule = load_schedule(SCHEDULE_FILE)
    global_config = schedule.get("global", {})
    all_secrets = get_all_secrets(schedule)
    print(f"\nLoaded {len(all_secrets)} secrets from schedule")

    # Connect to Vault
    vault = get_vault_client()
    print("Vault connection established")

    # Process each secret
    results: list[RotationResult] = []
    rotated = 0
    skipped = 0
    failed = 0

    for secret_config, interval_days in all_secrets:
        name = secret_config["name"]

        # Check if rotation is due
        if not should_rotate(vault, secret_config, interval_days):
            # Update next-rotation metric
            last = get_last_rotation_time(vault, secret_config["vault_path"])
            if last:
                next_ts = last.timestamp() + (interval_days * 86400)
                rotation_next_timestamp.labels(
                    service=secret_config.get("service", "unknown"),
                    secret=name,
                ).set(next_ts)
            skipped += 1
            continue

        # Rotate
        result = rotate_secret(vault, secret_config, global_config)
        results.append(result)

        if result.status == RotationStatus.SUCCESS:
            rotated += 1
        elif result.status == RotationStatus.SKIPPED:
            skipped += 1
        else:
            failed += 1
            # Immediate notification for failures
            if global_config.get("notification_on_failure") == "immediate":
                send_immediate_failure(result)

    # Push metrics to Prometheus
    try:
        push_to_gateway(
            PROMETHEUS_PUSHGATEWAY,
            job="secret_rotation",
            registry=registry,
        )
        print("\nMetrics pushed to Prometheus")
    except Exception as e:
        print(f"\nWARNING: Failed to push metrics: {e}")

    # Send daily digest
    notify_mode = global_config.get("notification_on_success", "digest")
    if notify_mode == "digest":
        send_mattermost_notification(results, is_digest=True)
    elif notify_mode == "immediate":
        send_mattermost_notification(results, is_digest=False)

    # Summary
    print("\n" + "=" * 72)
    print("Rotation run complete!")
    print(f"  Rotated:  {rotated}")
    print(f"  Skipped:  {skipped}")
    print(f"  Failed:   {failed}")
    print(f"  Total:    {len(all_secrets)}")
    if DRY_RUN:
        print("  (DRY RUN — no actual changes)")
    print("=" * 72)

    if failed > 0:
        exit(1)


if __name__ == "__main__":
    main()
