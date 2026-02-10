#!/usr/bin/env python3
"""
SYSTEM 1 -- BACKUP FORTRESS: SDK Client
Omni Quantum Elite AI Coding System -- Data Protection Layer

Python client for the Backup Fortress APIs. Provides methods for triggering
backups, checking status, viewing history, managing schedules, and running
restore verifications.
"""

from typing import Any

import httpx
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic Response Models
# ---------------------------------------------------------------------------


class BackupJobInfo(BaseModel):
    job_id: str = ""
    service: str = ""
    status: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    size_bytes: int | None = None
    snapshot_id: str | None = None
    error: str | None = None
    trace_id: str = ""


class BackupStatusResponse(BaseModel):
    active_jobs: dict[str, Any] = Field(default_factory=dict)
    active_count: int = 0
    scheduler_running: bool = False
    scheduled_jobs: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = ""


class BackupHistoryResponse(BaseModel):
    history: list[dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    days: int = 30
    timestamp: str = ""


class ScheduleResponse(BaseModel):
    schedule: dict[str, str] = Field(default_factory=dict)
    scheduled_jobs: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = ""


class VerifyResultInfo(BaseModel):
    verify_id: str = ""
    service: str = ""
    status: str = ""
    passed: bool = False
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    snapshot_id: str | None = None
    checks: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    trace_id: str = ""


class VerifyStatusResponse(BaseModel):
    active_verifications: dict[str, Any] = Field(default_factory=dict)
    active_count: int = 0
    last_results: dict[str, Any] = Field(default_factory=dict)
    scheduler_running: bool = False
    next_scheduled_run: str | None = None
    timestamp: str = ""


class VerifyHistoryResponse(BaseModel):
    history: list[dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    days: int = 30
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class BackupClientError(Exception):
    """Raised when a Backup Fortress API call fails."""

    def __init__(self, message: str, status_code: int | None = None, detail: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class BackupClient:
    """Client for the Backup Fortress REST APIs.

    Provides methods for backup management, restore verification,
    schedule configuration, and history retrieval.

    Args:
        base_url: Backup orchestrator URL (default: http://omni-restic-server:8000).
        verifier_url: Restore verifier URL (default: http://omni-restore-verifier:8001).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = "http://omni-restic-server:8000",
        verifier_url: str = "http://omni-restore-verifier:8001",
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.verifier_url = verifier_url.rstrip("/")
        self.timeout = timeout

    # ───────────────────────────────────────────────────────────────
    # Internal Helpers
    # ───────────────────────────────────────────────────────────────

    def _get(self, url: str, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request and return parsed JSON."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.get(f"{url}{path}", params=params)
            if resp.status_code >= 400:
                raise BackupClientError(
                    f"GET {path} returned {resp.status_code}",
                    status_code=resp.status_code,
                    detail=resp.text[:500],
                )
            return resp.json()

    def _post(self, url: str, path: str, data: dict[str, Any] | None = None) -> Any:
        """Make a POST request and return parsed JSON."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.post(f"{url}{path}", json=data or {})
            if resp.status_code >= 400:
                raise BackupClientError(
                    f"POST {path} returned {resp.status_code}",
                    status_code=resp.status_code,
                    detail=resp.text[:500],
                )
            return resp.json()

    def _put(self, url: str, path: str, data: dict[str, Any] | None = None) -> Any:
        """Make a PUT request and return parsed JSON."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.put(f"{url}{path}", json=data or {})
            if resp.status_code >= 400:
                raise BackupClientError(
                    f"PUT {path} returned {resp.status_code}",
                    status_code=resp.status_code,
                    detail=resp.text[:500],
                )
            return resp.json()

    def _delete(self, url: str, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a DELETE request and return parsed JSON."""
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.delete(f"{url}{path}", params=params)
            if resp.status_code >= 400:
                raise BackupClientError(
                    f"DELETE {path} returned {resp.status_code}",
                    status_code=resp.status_code,
                    detail=resp.text[:500],
                )
            return resp.json()

    # ───────────────────────────────────────────────────────────────
    # Backup Operations
    # ───────────────────────────────────────────────────────────────

    def backup(self, service: str) -> dict[str, Any]:
        """Trigger a backup for a specific service.

        Args:
            service: Service name (e.g. 'postgresql', 'redis', 'vault').

        Returns:
            Response with status, message, and job details.

        Raises:
            BackupClientError: If the service is unknown or backup fails to start.
        """
        return self._post(self.base_url, f"/backup/{service}")

    def backup_all(self) -> dict[str, Any]:
        """Trigger backup for all configured targets.

        Returns:
            Response with status and message confirming initiation.
        """
        return self._post(self.base_url, "/backup/all")

    def status(self) -> BackupStatusResponse:
        """Get current status of all backup jobs.

        Returns:
            BackupStatusResponse with active jobs, scheduler state,
            and upcoming scheduled jobs.
        """
        data = self._get(self.base_url, "/backup/status")
        return BackupStatusResponse(**data)

    def history(self, days: int = 30) -> BackupHistoryResponse:
        """Get backup history for the last N days.

        Args:
            days: Number of days of history to retrieve (default 30).

        Returns:
            BackupHistoryResponse with list of completed backup jobs.
        """
        data = self._get(self.base_url, "/backup/history", params={"days": days})
        return BackupHistoryResponse(**data)

    def delete_snapshot(
        self, service: str, snapshot_id: str, confirmation_token: str
    ) -> dict[str, Any]:
        """Delete a specific backup snapshot.

        Args:
            service: Service name.
            snapshot_id: Restic snapshot ID to delete.
            confirmation_token: Required confirmation token for deletion.

        Returns:
            Response confirming deletion.

        Raises:
            BackupClientError: If token is invalid or deletion fails.
        """
        return self._delete(
            self.base_url,
            f"/backup/{service}/{snapshot_id}",
            params={"confirmation_token": confirmation_token},
        )

    # ───────────────────────────────────────────────────────────────
    # Schedule Management
    # ───────────────────────────────────────────────────────────────

    def schedule(self) -> ScheduleResponse:
        """Get the current backup schedule configuration.

        Returns:
            ScheduleResponse with cron expressions per target
            and scheduled job details.
        """
        data = self._get(self.base_url, "/backup/schedule")
        return ScheduleResponse(**data)

    def update_schedule(self, config: dict[str, str]) -> dict[str, Any]:
        """Update the backup schedule configuration.

        Args:
            config: Dictionary mapping target names to cron expressions.
                Example: {"postgresql": "0 */4 * * *", "redis": "*/30 * * * *"}

        Returns:
            Response confirming the schedule update.
        """
        return self._put(self.base_url, "/backup/schedule", data=config)

    # ───────────────────────────────────────────────────────────────
    # Verification Operations
    # ───────────────────────────────────────────────────────────────

    def verify(self, service: str) -> dict[str, Any]:
        """Trigger restore verification for a specific service.

        Args:
            service: Service name to verify (e.g. 'postgresql', 'redis').

        Returns:
            Response with verification status and trace ID.

        Raises:
            BackupClientError: If the service is unknown or verification
                is already running.
        """
        return self._post(self.verifier_url, f"/verify/{service}")

    def verify_status(self) -> VerifyStatusResponse:
        """Get current status of all restore verifications.

        Returns:
            VerifyStatusResponse with active verifications, last results,
            and next scheduled run time.
        """
        data = self._get(self.verifier_url, "/verify/status")
        return VerifyStatusResponse(**data)

    def verify_history(self, days: int = 30) -> VerifyHistoryResponse:
        """Get verification history for the last N days.

        Args:
            days: Number of days of history to retrieve (default 30).

        Returns:
            VerifyHistoryResponse with list of completed verifications.
        """
        data = self._get(self.verifier_url, "/verify/history", params={"days": days})
        return VerifyHistoryResponse(**data)

    # ───────────────────────────────────────────────────────────────
    # Health Checks
    # ───────────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Check backup orchestrator health.

        Returns:
            Health status dict with service name and timestamp.
        """
        return self._get(self.base_url, "/health")

    def verifier_health(self) -> dict[str, Any]:
        """Check restore verifier health.

        Returns:
            Health status dict with service name and timestamp.
        """
        return self._get(self.verifier_url, "/health")

    def ready(self) -> dict[str, Any]:
        """Check backup orchestrator readiness.

        Returns:
            Readiness status with scheduler state.
        """
        return self._get(self.base_url, "/ready")

    def verifier_ready(self) -> dict[str, Any]:
        """Check restore verifier readiness.

        Returns:
            Readiness status with scheduler state.
        """
        return self._get(self.verifier_url, "/ready")
