#!/usr/bin/env python3
"""
SYSTEM 1 -- BACKUP FORTRESS: Retention Manager
Omni Quantum Elite AI Coding System -- Data Protection Layer

Module imported by the backup orchestrator. Manages Restic retention policies
using `restic forget` with configurable keep rules and `--prune`.

Policy defaults:
  --keep-hourly 24
  --keep-daily 30
  --keep-weekly 52
  --keep-monthly unlimited
  --prune

Logs space reclaimed after each prune operation.

Metrics:
  retention_prune_space_reclaimed_bytes{service}
  retention_snapshots_removed_total{service}
"""

import asyncio
import json
import os
import re
import time
from typing import Any

import structlog
from prometheus_client import CollectorRegistry, Counter, Gauge

logger = structlog.get_logger("retention-manager")


class RetentionManager:
    """Manages Restic retention policies across all backup targets.

    Args:
        minio_endpoint: MinIO S3 endpoint URL.
        minio_access_key: MinIO access key.
        minio_secret_key: MinIO secret key.
        restic_password: Password for Restic repositories.
        targets: List of backup target service names.
        registry: Prometheus CollectorRegistry for metrics.
        keep_hourly: Number of hourly snapshots to keep.
        keep_daily: Number of daily snapshots to keep.
        keep_weekly: Number of weekly snapshots to keep.
        keep_monthly: Number of monthly snapshots to keep (0 = unlimited).
    """

    def __init__(
        self,
        minio_endpoint: str,
        minio_access_key: str,
        minio_secret_key: str,
        restic_password: str,
        targets: list[str],
        registry: CollectorRegistry,
        keep_hourly: int = 24,
        keep_daily: int = 30,
        keep_weekly: int = 52,
        keep_monthly: int = 0,
    ):
        self.minio_endpoint = minio_endpoint
        self.minio_access_key = minio_access_key
        self.minio_secret_key = minio_secret_key
        self.restic_password = restic_password
        self.targets = targets
        self.keep_hourly = keep_hourly
        self.keep_daily = keep_daily
        self.keep_weekly = keep_weekly
        self.keep_monthly = keep_monthly

        # Prometheus metrics
        self.prune_space_reclaimed = Gauge(
            "retention_prune_space_reclaimed_bytes",
            "Bytes reclaimed by last retention prune",
            ["service"],
            registry=registry,
        )

        self.snapshots_removed = Counter(
            "retention_snapshots_removed_total",
            "Total number of snapshots removed by retention",
            ["service"],
            registry=registry,
        )

    def _restic_env(self, service: str) -> dict[str, str]:
        """Build environment variables for a Restic command."""
        repo = f"s3:{self.minio_endpoint}/omni-backups-{service}"
        env = os.environ.copy()
        env.update({
            "RESTIC_REPOSITORY": repo,
            "RESTIC_PASSWORD": self.restic_password,
            "AWS_ACCESS_KEY_ID": self.minio_access_key,
            "AWS_SECRET_ACCESS_KEY": self.minio_secret_key,
        })
        return env

    async def _run_command(
        self, cmd: list[str], env: dict[str, str] | None = None, timeout: int = 3600
    ) -> tuple[int, str, str]:
        """Run a subprocess asynchronously and return (returncode, stdout, stderr)."""
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=merged_env,
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

    async def _get_repo_stats(self, service: str) -> dict[str, Any]:
        """Get repository stats before pruning for comparison."""
        env = self._restic_env(service)
        rc, stdout, stderr = await self._run_command(
            ["restic", "stats", "--json"], env=env, timeout=300
        )
        if rc != 0:
            return {"total_size": 0, "total_file_count": 0}

        try:
            data = json.loads(stdout)
            return {
                "total_size": data.get("total_size", 0),
                "total_file_count": data.get("total_file_count", 0),
            }
        except json.JSONDecodeError:
            return {"total_size": 0, "total_file_count": 0}

    async def _count_snapshots(self, service: str) -> int:
        """Count current snapshots in repository."""
        env = self._restic_env(service)
        rc, stdout, stderr = await self._run_command(
            ["restic", "snapshots", "--json"], env=env, timeout=120
        )
        if rc != 0:
            return 0
        try:
            snaps = json.loads(stdout)
            return len(snaps) if isinstance(snaps, list) else 0
        except json.JSONDecodeError:
            return 0

    def _parse_forget_output(self, stdout: str) -> int:
        """Parse restic forget output to count removed snapshots."""
        removed = 0
        try:
            data = json.loads(stdout)
            if isinstance(data, list):
                for group in data:
                    remove_list = group.get("remove", [])
                    if isinstance(remove_list, list):
                        removed += len(remove_list)
            elif isinstance(data, dict):
                remove_list = data.get("remove", [])
                if isinstance(remove_list, list):
                    removed += len(remove_list)
        except json.JSONDecodeError:
            # Fallback: count "remove" lines in plain text
            for line in stdout.split("\n"):
                if "remove" in line.lower():
                    removed += 1
        return removed

    def _parse_prune_space(self, stderr: str, stdout: str) -> int:
        """Parse restic prune output to determine space reclaimed in bytes."""
        combined = stdout + "\n" + stderr
        reclaimed = 0

        # Look for patterns like "freed 123.456 MiB" or "reclaimed 123 B"
        patterns = [
            r"freed\s+([\d.]+)\s*(B|KiB|MiB|GiB|TiB)",
            r"reclaimed\s+([\d.]+)\s*(B|KiB|MiB|GiB|TiB)",
            r"removed\s+([\d.]+)\s*(B|KiB|MiB|GiB|TiB)",
            r"will free\s+([\d.]+)\s*(B|KiB|MiB|GiB|TiB)",
        ]

        multipliers = {
            "B": 1,
            "KiB": 1024,
            "MiB": 1024 * 1024,
            "GiB": 1024 * 1024 * 1024,
            "TiB": 1024 * 1024 * 1024 * 1024,
        }

        for pattern in patterns:
            matches = re.findall(pattern, combined, re.IGNORECASE)
            for value_str, unit in matches:
                try:
                    value = float(value_str)
                    multiplier = multipliers.get(unit, 1)
                    reclaimed += int(value * multiplier)
                except ValueError:
                    continue

        return reclaimed

    async def prune_service(self, service: str) -> dict[str, Any]:
        """Run retention policy on a single service's Restic repository.

        Executes: restic forget --keep-hourly 24 --keep-daily 30
                  --keep-weekly 52 --keep-monthly unlimited --prune

        Returns:
            Dictionary with prune results including snapshots removed
            and space reclaimed.
        """
        log = logger.bind(service=service)
        log.info("retention_prune_started")
        start_time = time.monotonic()

        env = self._restic_env(service)

        # Get pre-prune stats
        pre_stats = await self._get_repo_stats(service)
        pre_snapshots = await self._count_snapshots(service)

        # Build the forget command
        cmd = [
            "restic", "forget",
            "--keep-hourly", str(self.keep_hourly),
            "--keep-daily", str(self.keep_daily),
            "--keep-weekly", str(self.keep_weekly),
            "--prune",
            "--json",
        ]

        # keep-monthly: 0 means unlimited
        if self.keep_monthly > 0:
            cmd.extend(["--keep-monthly", str(self.keep_monthly)])

        rc, stdout, stderr = await self._run_command(cmd, env=env, timeout=3600)

        duration = time.monotonic() - start_time

        if rc != 0:
            log.error(
                "retention_prune_failed",
                return_code=rc,
                stderr=stderr[:500],
                duration_seconds=round(duration, 2),
            )
            return {
                "service": service,
                "status": "failed",
                "error": stderr[:500],
                "duration_seconds": round(duration, 2),
            }

        # Count removed snapshots
        snapshots_removed = self._parse_forget_output(stdout)

        # Calculate space reclaimed
        post_stats = await self._get_repo_stats(service)
        post_snapshots = await self._count_snapshots(service)

        space_reclaimed = max(0, pre_stats["total_size"] - post_stats["total_size"])

        # If we couldn't calculate from stats, try parsing output
        if space_reclaimed == 0:
            space_reclaimed = self._parse_prune_space(stderr, stdout)

        # If snapshots_removed is 0 but we can calculate from counts
        if snapshots_removed == 0:
            snapshots_removed = max(0, pre_snapshots - post_snapshots)

        # Update Prometheus metrics
        self.prune_space_reclaimed.labels(service=service).set(space_reclaimed)
        self.snapshots_removed.labels(service=service).inc(snapshots_removed)

        result = {
            "service": service,
            "status": "completed",
            "snapshots_before": pre_snapshots,
            "snapshots_after": post_snapshots,
            "snapshots_removed": snapshots_removed,
            "space_before_bytes": pre_stats["total_size"],
            "space_after_bytes": post_stats["total_size"],
            "space_reclaimed_bytes": space_reclaimed,
            "duration_seconds": round(duration, 2),
        }

        log.info(
            "retention_prune_completed",
            **result,
        )

        return result

    async def run_retention(self) -> list[dict[str, Any]]:
        """Run retention pruning across all backup targets.

        This is the main entry point called by the scheduler.
        Processes each target sequentially to avoid overwhelming the storage.

        Returns:
            List of prune results for each target.
        """
        log = logger.bind(task="retention_run")
        log.info(
            "retention_run_started",
            targets=self.targets,
            policy={
                "keep_hourly": self.keep_hourly,
                "keep_daily": self.keep_daily,
                "keep_weekly": self.keep_weekly,
                "keep_monthly": "unlimited" if self.keep_monthly == 0 else self.keep_monthly,
            },
        )

        start_time = time.monotonic()
        results = []
        total_reclaimed = 0
        total_removed = 0

        for service in self.targets:
            try:
                result = await self.prune_service(service)
                results.append(result)
                if result["status"] == "completed":
                    total_reclaimed += result.get("space_reclaimed_bytes", 0)
                    total_removed += result.get("snapshots_removed", 0)
            except Exception as exc:
                log.error("retention_prune_error", service=service, error=str(exc))
                results.append({
                    "service": service,
                    "status": "error",
                    "error": str(exc),
                })

        total_duration = time.monotonic() - start_time

        log.info(
            "retention_run_completed",
            targets_processed=len(results),
            total_snapshots_removed=total_removed,
            total_space_reclaimed_bytes=total_reclaimed,
            total_space_reclaimed_mb=round(total_reclaimed / (1024 * 1024), 2),
            total_duration_seconds=round(total_duration, 2),
        )

        return results
