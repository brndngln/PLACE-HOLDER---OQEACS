# ===========================================================================
# SYSTEM 17 -- AI CODER BETA (SWE-Agent): Python SDK Client
# Omni Quantum Elite AI Coding System -- SWE-Agent Task Handler Client
#
# Async SDK for interacting with the SWE-Agent Task Handler (port 8001).
# Designed as an async context manager with built-in retry logic,
# structured logging, and Pydantic response models.
#
# Usage:
#   async with SWEAgentClient() as client:
#       task = await client.create_task(
#           task_type="bug-fix",
#           issue_url="http://omni-gitea:3000/org/repo/issues/42",
#           repository="org/repo",
#           description="NullPointerException in payment flow",
#       )
#       detail = await client.get_task(task.task_id)
# ===========================================================================

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx
import structlog
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        (
            structlog.dev.ConsoleRenderer()
            if os.getenv("LOG_FORMAT") == "console"
            else structlog.processors.JSONRenderer()
        ),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.get_config().get("min_level", 0)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("swe-agent-sdk")


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    """SWE-Agent task lifecycle status."""

    RECEIVED = "RECEIVED"
    CONTEXT_COMPILING = "CONTEXT_COMPILING"
    REPRODUCTION = "REPRODUCTION"
    ROOT_CAUSE_ANALYSIS = "ROOT_CAUSE_ANALYSIS"
    FIX_IMPLEMENTATION = "FIX_IMPLEMENTATION"
    VERIFICATION = "VERIFICATION"
    QUALITY_CHECK = "QUALITY_CHECK"
    PR_CREATED = "PR_CREATED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    CANCELLED = "CANCELLED"


class Task(BaseModel):
    """Response model for task creation and status updates."""

    task_id: str
    task_type: str
    status: TaskStatus
    repository: str
    issue_url: str
    severity: str
    created_at: str
    updated_at: str
    message: str = ""


class ReproductionResult(BaseModel):
    """Reproduction stage result."""

    success: bool = False
    error_output: str = ""
    exit_code: int = -1
    duration_seconds: float = 0.0
    environment_info: dict[str, str] = Field(default_factory=dict)
    stack_trace: str = ""


class RootCauseReport(BaseModel):
    """Root cause analysis report."""

    root_cause: str = ""
    affected_files: list[str] = Field(default_factory=list)
    affected_functions: list[str] = Field(default_factory=list)
    anti_patterns_detected: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    analysis_method: str = ""


class FixDetail(BaseModel):
    """Fix implementation details."""

    explanation: str = ""
    files_changed: list[str] = Field(default_factory=list)
    diff_summary: str = ""
    backward_compatible: bool = True
    new_tests_added: int = 0
    lines_added: int = 0
    lines_removed: int = 0


class VerificationResult(BaseModel):
    """Verification stage results."""

    reproduction_passes: bool = False
    test_suite_passes: bool = False
    new_tests_pass: bool = False
    regression_tests_pass: bool = False
    total_tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    coverage_delta: float = 0.0


class QualityCheckResult(BaseModel):
    """Quality check results from Code Scorer and Gate Engine."""

    code_score: float = 0.0
    gate_passed: bool = False
    dimensions: dict[str, float] = Field(default_factory=dict)
    gate_details: dict[str, Any] = Field(default_factory=dict)
    lint_passed: bool = False
    security_scan_passed: bool = False


class PRInfo(BaseModel):
    """Pull request information."""

    pr_url: str = ""
    pr_number: int = 0
    branch_name: str = ""
    title: str = ""
    labels: list[str] = Field(default_factory=list)


class TaskDetail(BaseModel):
    """Full task detail with all diagnostic data."""

    task_id: str
    task_type: str
    status: TaskStatus
    repository: str
    issue_url: str
    description: str
    reproduction_steps: list[str] = Field(default_factory=list)
    expected_behavior: str = ""
    severity: str
    created_at: str
    updated_at: str
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    message: str = ""
    reproduction_result: Optional[ReproductionResult] = None
    root_cause_report: Optional[RootCauseReport] = None
    fix_detail: Optional[FixDetail] = None
    verification_result: Optional[VerificationResult] = None
    quality_check_result: Optional[QualityCheckResult] = None
    pr_info: Optional[PRInfo] = None
    rejection_feedback: str = ""
    stage_history: list[dict[str, str]] = Field(default_factory=list)


class TaskSummary(BaseModel):
    """Lightweight task summary for list endpoints."""

    task_id: str
    task_type: str
    status: TaskStatus
    repository: str
    severity: str
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class SWEAgentClientError(Exception):
    """Base exception for SWE-Agent SDK errors."""

    def __init__(self, message: str, status_code: int | None = None, detail: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class SWEAgentNotFoundError(SWEAgentClientError):
    """Raised when a task is not found (HTTP 404)."""

    pass


class SWEAgentValidationError(SWEAgentClientError):
    """Raised when request validation fails (HTTP 422)."""

    pass


class SWEAgentConflictError(SWEAgentClientError):
    """Raised when a state conflict occurs (HTTP 409)."""

    pass


class SWEAgentServerError(SWEAgentClientError):
    """Raised when the server returns a 5xx error."""

    pass


# ---------------------------------------------------------------------------
# SWE-Agent SDK Client
# ---------------------------------------------------------------------------

class SWEAgentClient:
    """
    Async client for the SWE-Agent Task Handler API.

    Designed as an async context manager with automatic connection pooling,
    exponential backoff retry logic, and structured logging.

    Args:
        base_url: Base URL of the SWE-Agent Task Handler service.
        timeout: Default request timeout in seconds.
        max_retries: Maximum number of retry attempts for transient failures.
        backoff_base: Base value for exponential backoff (seconds).
        backoff_max: Maximum backoff duration (seconds).
        headers: Additional headers to send with every request.

    Example:
        async with SWEAgentClient(base_url="http://localhost:8001") as client:
            task = await client.create_task(
                task_type="bug-fix",
                issue_url="http://gitea/org/repo/issues/1",
                repository="org/repo",
                description="NPE in checkout",
            )
            print(task.task_id, task.status)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        backoff_max: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._extra_headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> SWEAgentClient:
        """Open the underlying HTTP connection pool."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "swe-agent-sdk/1.0.0",
                **self._extra_headers,
            },
        )
        logger.info("swe_agent_client_connected", base_url=self._base_url)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close the underlying HTTP connection pool."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("swe_agent_client_closed")

    @property
    def _http(self) -> httpx.AsyncClient:
        """Return the active HTTP client, raising if not in context manager."""
        if self._client is None:
            raise RuntimeError(
                "SWEAgentClient must be used as an async context manager: "
                "'async with SWEAgentClient() as client:'"
            )
        return self._client

    # ------------------------------------------------------------------
    # Internal retry logic
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """
        Execute an HTTP request with exponential backoff retry.

        Retries on:
        - HTTP 5xx server errors
        - Network transport errors (connection refused, timeout, etc.)

        Does NOT retry on:
        - HTTP 4xx client errors (immediately raises appropriate exception)
        """
        effective_timeout = timeout or self._timeout
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await self._http.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    timeout=effective_timeout,
                )

                # Handle specific HTTP error codes
                if response.status_code == 404:
                    detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                    raise SWEAgentNotFoundError(
                        f"Resource not found: {path}",
                        status_code=404,
                        detail=detail,
                    )
                if response.status_code == 422:
                    detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                    raise SWEAgentValidationError(
                        f"Validation error: {path}",
                        status_code=422,
                        detail=detail,
                    )
                if response.status_code == 409:
                    detail = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                    raise SWEAgentConflictError(
                        f"Conflict: {path}",
                        status_code=409,
                        detail=detail,
                    )
                if response.status_code >= 500:
                    logger.warning(
                        "server_error_retry",
                        method=method,
                        path=path,
                        status=response.status_code,
                        attempt=attempt + 1,
                    )
                    last_exc = SWEAgentServerError(
                        f"Server error {response.status_code}",
                        status_code=response.status_code,
                        detail=response.text[:500],
                    )
                    if attempt < self._max_retries - 1:
                        backoff = min(self._backoff_base ** attempt, self._backoff_max)
                        await asyncio.sleep(backoff)
                        continue
                    raise last_exc

                response.raise_for_status()
                return response

            except (SWEAgentNotFoundError, SWEAgentValidationError, SWEAgentConflictError):
                raise
            except SWEAgentServerError:
                if attempt == self._max_retries - 1:
                    raise
            except httpx.TransportError as exc:
                last_exc = exc
                logger.warning(
                    "transport_error_retry",
                    method=method,
                    path=path,
                    error=str(exc),
                    attempt=attempt + 1,
                )
                if attempt < self._max_retries - 1:
                    backoff = min(self._backoff_base ** attempt, self._backoff_max)
                    await asyncio.sleep(backoff)
                    continue
                raise SWEAgentClientError(
                    f"Transport error after {self._max_retries} attempts: {exc}",
                    detail=str(exc),
                ) from exc

        # Should not reach here, but just in case
        raise SWEAgentClientError(
            f"Request failed after {self._max_retries} attempts",
            detail=str(last_exc),
        )

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def create_task(
        self,
        *,
        task_type: str,
        issue_url: str,
        repository: str,
        description: str,
        reproduction_steps: list[str] | None = None,
        expected_behavior: str = "",
        severity: str = "medium",
    ) -> Task:
        """
        Create a new SWE-Agent task.

        This initiates the 9-stage lifecycle: RECEIVED -> CONTEXT_COMPILING ->
        REPRODUCTION -> ROOT_CAUSE_ANALYSIS -> FIX_IMPLEMENTATION -> VERIFICATION ->
        QUALITY_CHECK -> PR_CREATED -> COMPLETE.

        Args:
            task_type: One of bug-fix, security-patch, performance-fix,
                       dependency-update, test-coverage.
            issue_url: Full URL of the Gitea issue.
            repository: Repository in 'owner/repo' format.
            description: Human-readable description of the problem.
            reproduction_steps: Ordered list of steps to reproduce the issue.
            expected_behavior: What the correct behavior should be.
            severity: One of critical, high, medium, low.

        Returns:
            Task: The newly created task with ID and initial status.

        Raises:
            SWEAgentValidationError: If the payload fails validation.
            SWEAgentServerError: If the server returns a 5xx error.
            SWEAgentClientError: On transport or unexpected errors.
        """
        payload: dict[str, Any] = {
            "task_type": task_type,
            "issue_url": issue_url,
            "repository": repository,
            "description": description,
            "reproduction_steps": reproduction_steps or [],
            "expected_behavior": expected_behavior,
            "severity": severity,
        }

        logger.info(
            "creating_task",
            task_type=task_type,
            repository=repository,
            severity=severity,
        )

        response = await self._request("POST", "/tasks", json=payload)
        task = Task.model_validate(response.json())

        logger.info(
            "task_created",
            task_id=task.task_id,
            task_type=task.task_type,
            status=task.status.value,
        )
        return task

    async def get_task(self, task_id: str) -> TaskDetail:
        """
        Get full task detail including reproduction results, root cause
        analysis, fix details, verification results, and PR info.

        Args:
            task_id: The unique task identifier (e.g. 'swe-a1b2c3d4e5f6').

        Returns:
            TaskDetail: Complete task information with all diagnostic data.

        Raises:
            SWEAgentNotFoundError: If the task does not exist.
            SWEAgentServerError: If the server returns a 5xx error.
        """
        logger.debug("getting_task", task_id=task_id)
        response = await self._request("GET", f"/tasks/{task_id}")
        detail = TaskDetail.model_validate(response.json())
        logger.debug("task_retrieved", task_id=task_id, status=detail.status.value)
        return detail

    async def list_tasks(
        self,
        *,
        task_type: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        repository: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TaskSummary]:
        """
        List tasks with optional filters and pagination.

        Args:
            task_type: Filter by task type (e.g. 'bug-fix').
            status: Filter by status (e.g. 'COMPLETE').
            severity: Filter by severity (e.g. 'critical').
            repository: Filter by repository (e.g. 'org/repo').
            limit: Maximum number of results (1-1000, default 100).
            offset: Result offset for pagination.

        Returns:
            list[TaskSummary]: Lightweight task summaries sorted by
                               creation time descending.

        Raises:
            SWEAgentServerError: If the server returns a 5xx error.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if task_type:
            params["task_type"] = task_type
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        if repository:
            params["repository"] = repository

        logger.debug("listing_tasks", filters=params)
        response = await self._request("GET", "/tasks", params=params)
        data = response.json()
        summaries = [TaskSummary.model_validate(item) for item in data]
        logger.debug("tasks_listed", count=len(summaries))
        return summaries

    async def approve_task(self, task_id: str) -> Task:
        """
        Approve a completed task, signalling that the PR can be merged.

        Args:
            task_id: The unique task identifier.

        Returns:
            Task: Updated task in COMPLETE status.

        Raises:
            SWEAgentNotFoundError: If the task does not exist.
            SWEAgentConflictError: If the task is not in an approvable state.
            SWEAgentServerError: If the server returns a 5xx error.
        """
        logger.info("approving_task", task_id=task_id)
        response = await self._request("POST", f"/tasks/{task_id}/approve")
        task = Task.model_validate(response.json())
        logger.info("task_approved", task_id=task_id, status=task.status.value)
        return task

    async def reject_task(self, task_id: str, feedback: str) -> Task:
        """
        Reject a task with feedback. The feedback is stored as an anti-pattern
        so the SWE-Agent can learn from the rejection.

        Args:
            task_id: The unique task identifier.
            feedback: Reason for rejection; stored for future learning.

        Returns:
            Task: Updated task in REJECTED status.

        Raises:
            SWEAgentNotFoundError: If the task does not exist.
            SWEAgentConflictError: If the task cannot be rejected.
            SWEAgentServerError: If the server returns a 5xx error.
        """
        logger.info("rejecting_task", task_id=task_id, feedback_length=len(feedback))
        response = await self._request(
            "POST",
            f"/tasks/{task_id}/reject",
            json={"feedback": feedback},
        )
        task = Task.model_validate(response.json())
        logger.info("task_rejected", task_id=task_id, status=task.status.value)
        return task

    async def delete_task(self, task_id: str) -> Task:
        """
        Cancel and remove a task. Running tasks are marked CANCELLED.

        Args:
            task_id: The unique task identifier.

        Returns:
            Task: The cancelled task.

        Raises:
            SWEAgentNotFoundError: If the task does not exist.
            SWEAgentServerError: If the server returns a 5xx error.
        """
        logger.info("deleting_task", task_id=task_id)
        response = await self._request("DELETE", f"/tasks/{task_id}")
        task = Task.model_validate(response.json())
        logger.info("task_deleted", task_id=task_id, status=task.status.value)
        return task

    async def wait_for_completion(
        self,
        task_id: str,
        *,
        poll_interval: float = 10.0,
        timeout: float = 3600.0,
    ) -> TaskDetail:
        """
        Poll a task until it reaches a terminal status.

        Terminal statuses: COMPLETE, FAILED, REJECTED, HUMAN_REVIEW, CANCELLED.

        Args:
            task_id: The unique task identifier.
            poll_interval: Seconds between status polls (default 10).
            timeout: Maximum wait time in seconds (default 3600).

        Returns:
            TaskDetail: The task in its terminal state.

        Raises:
            TimeoutError: If the task does not complete within the timeout.
            SWEAgentNotFoundError: If the task does not exist.
        """
        terminal_statuses = {
            TaskStatus.COMPLETE,
            TaskStatus.FAILED,
            TaskStatus.REJECTED,
            TaskStatus.HUMAN_REVIEW,
            TaskStatus.CANCELLED,
        }

        logger.info("waiting_for_completion", task_id=task_id, timeout=timeout)
        elapsed = 0.0

        while elapsed < timeout:
            detail = await self.get_task(task_id)
            if detail.status in terminal_statuses:
                logger.info(
                    "task_reached_terminal",
                    task_id=task_id,
                    status=detail.status.value,
                    elapsed_seconds=round(elapsed, 1),
                )
                return detail
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"Task '{task_id}' did not reach a terminal status within {timeout}s"
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Check the health of the Task Handler service.

        Returns:
            dict: Health status response.
        """
        response = await self._request("GET", "/health")
        return response.json()

    async def readiness_check(self) -> dict[str, Any]:
        """
        Check the readiness of the Task Handler service and its dependencies.

        Returns:
            dict: Readiness status with individual dependency checks.
        """
        response = await self._request("GET", "/ready")
        return response.json()
