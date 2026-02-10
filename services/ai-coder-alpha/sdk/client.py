#!/usr/bin/env python3
"""
SYSTEM 16 -- AI CODER ALPHA: Python SDK Client
Omni Quantum Elite AI Coding System -- AI Coding Agent Layer

Async Python client for the OpenHands Task Orchestrator API.  Provides
typed methods for all task lifecycle operations with automatic retry logic,
Pydantic response models, and async context manager support.

Usage:
    async with OpenHandsClient() as client:
        task = await client.create_task(
            task_type="feature-build",
            description="Add user authentication to the API",
            repository="my-service",
        )
        detail = await client.get_task(task.task_id)
        print(detail.status)

Requirements: httpx, pydantic
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from types import TracebackType
from typing import Any, Optional, Type

import httpx
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskType(str, Enum):
    """Supported coding task types."""
    FEATURE_BUILD = "feature-build"
    BUG_FIX = "bug-fix"
    REFACTOR = "refactor"
    TEST_GEN = "test-gen"


class TaskStatus(str, Enum):
    """Task lifecycle statuses."""
    RECEIVED = "received"
    CONTEXT_COMPILING = "context_compiling"
    SPEC_GENERATING = "spec_generating"
    SPEC_REVIEW = "spec_review"
    CODING = "coding"
    SELF_REVIEW = "self_review"
    TESTING = "testing"
    GATE_CHECK = "gate_check"
    PR_CREATED = "pr_created"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PENDING_HUMAN_REVIEW = "pending_human_review"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ScoreDetail(BaseModel):
    """Code Scorer 10-dimension score detail."""
    correctness: float = 0.0
    completeness: float = 0.0
    maintainability: float = 0.0
    readability: float = 0.0
    security: float = 0.0
    performance: float = 0.0
    test_coverage: float = 0.0
    documentation: float = 0.0
    error_handling: float = 0.0
    best_practices: float = 0.0
    overall: float = 0.0


class GateCheckResult(BaseModel):
    """Gate Engine check results."""
    lint_passed: bool = False
    security_passed: bool = False
    complexity_passed: bool = False
    coverage_passed: bool = False
    coverage_pct: float = 0.0
    all_passed: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    """An artifact produced by a coding task."""
    artifact_id: str = ""
    name: str = ""
    artifact_type: str = ""
    path: str = ""
    size_bytes: int = 0
    created_at: str = ""


class Task(BaseModel):
    """Task creation response."""
    task_id: str
    status: str
    task_type: str
    repository: str
    working_branch: Optional[str] = None
    created_at: str


class TaskSummary(BaseModel):
    """Lightweight task summary for list responses."""
    task_id: str
    task_type: str
    status: str
    description: str
    repository: str
    branch: str
    complexity: str
    created_at: str
    updated_at: str
    pr_url: Optional[str] = None
    code_score_overall: Optional[float] = None


class TaskDetail(BaseModel):
    """Full task detail response with all lifecycle data."""
    task_id: str
    task_type: str
    status: str
    description: str
    repository: str
    branch: str
    target_language: str
    framework: Optional[str] = None
    complexity: str = "medium"
    spec: Optional[str] = None
    referenced_files: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)

    compiled_context: Optional[str] = None
    generated_spec: Optional[str] = None
    spec_score: Optional[ScoreDetail] = None
    code_score: Optional[ScoreDetail] = None
    gate_result: Optional[GateCheckResult] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    working_branch: Optional[str] = None

    spec_revision_count: int = 0
    coding_iteration_count: int = 0
    test_fix_count: int = 0

    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None

    logs: list[str] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    error_message: Optional[str] = None
    human_feedback: Optional[str] = None


class TaskListResponse(BaseModel):
    """Response from the list tasks endpoint."""
    total: int
    offset: int
    limit: int
    tasks: list[TaskSummary]


class TaskActionResponse(BaseModel):
    """Response from task action endpoints (approve/reject/cancel)."""
    task_id: str
    status: str
    message: str = ""
    feedback: Optional[str] = None


class TaskLogsResponse(BaseModel):
    """Response from the task logs endpoint."""
    task_id: str
    status: str
    log_count: int
    logs: str


class TaskArtifactsResponse(BaseModel):
    """Response from the task artifacts endpoint."""
    task_id: str
    artifact_count: int
    artifacts: list[Artifact]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str = ""
    system: str = ""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class OpenHandsError(Exception):
    """Base exception for OpenHands client errors."""

    def __init__(self, message: str, status_code: int = 0, detail: str = "") -> None:
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class OpenHandsNotFoundError(OpenHandsError):
    """Raised when a task is not found (404)."""
    pass


class OpenHandsValidationError(OpenHandsError):
    """Raised when request validation fails (422)."""
    pass


class OpenHandsConflictError(OpenHandsError):
    """Raised when a task state conflict occurs (400)."""
    pass


class OpenHandsServerError(OpenHandsError):
    """Raised when the server returns a 5xx error."""
    pass


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class OpenHandsClient:
    """Async client for the OpenHands Task Orchestrator API.

    Supports usage as an async context manager with automatic retry logic
    and exponential backoff for transient failures.

    Args:
        base_url: Base URL of the task orchestrator (default: http://localhost:3001).
        timeout: Default request timeout in seconds (default: 30.0).
        max_retries: Maximum number of retries for transient errors (default: 3).
        backoff_base: Base for exponential backoff calculation (default: 2.0).
        backoff_max: Maximum backoff delay in seconds (default: 30.0).
        headers: Optional additional headers to include in all requests.

    Example:
        async with OpenHandsClient(base_url="http://orchestrator:3001") as client:
            task = await client.create_task(
                task_type="bug-fix",
                description="Fix null pointer in auth module",
                repository="auth-service",
                target_language="python",
            )
            print(f"Created task: {task.task_id}")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3001",
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        backoff_max: float = 30.0,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max
        self._extra_headers = headers or {}
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> OpenHandsClient:
        """Enter the async context manager, creating the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "OpenHandsSDK/1.0.0",
                **self._extra_headers,
            },
        )
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit the async context manager, closing the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Return the underlying httpx client, raising if not initialized."""
        if self._client is None:
            raise RuntimeError(
                "OpenHandsClient is not initialized. Use 'async with OpenHandsClient() as client:' "
                "or call __aenter__ explicitly."
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.).
            path: API path (e.g., "/tasks").
            timeout: Optional per-request timeout override.
            **kwargs: Additional arguments passed to httpx.request.

        Returns:
            The httpx Response object.

        Raises:
            OpenHandsNotFoundError: If the resource is not found (404).
            OpenHandsValidationError: If request validation fails (422).
            OpenHandsConflictError: If there is a state conflict (400).
            OpenHandsServerError: If the server returns a 5xx error.
            OpenHandsError: For other HTTP errors.
        """
        effective_timeout = timeout or self._timeout
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                resp = await self.client.request(
                    method,
                    path,
                    timeout=effective_timeout,
                    **kwargs,
                )

                if resp.status_code == 404:
                    detail = self._extract_detail(resp)
                    raise OpenHandsNotFoundError(
                        f"Resource not found: {path}",
                        status_code=404,
                        detail=detail,
                    )

                if resp.status_code == 422:
                    detail = self._extract_detail(resp)
                    raise OpenHandsValidationError(
                        f"Validation error: {detail}",
                        status_code=422,
                        detail=detail,
                    )

                if resp.status_code == 400:
                    detail = self._extract_detail(resp)
                    raise OpenHandsConflictError(
                        f"Request error: {detail}",
                        status_code=400,
                        detail=detail,
                    )

                if resp.status_code >= 500:
                    detail = self._extract_detail(resp)
                    if attempt < self._max_retries - 1:
                        delay = min(self._backoff_base ** attempt, self._backoff_max)
                        await asyncio.sleep(delay)
                        continue
                    raise OpenHandsServerError(
                        f"Server error (HTTP {resp.status_code})",
                        status_code=resp.status_code,
                        detail=detail,
                    )

                resp.raise_for_status()
                return resp

            except (OpenHandsNotFoundError, OpenHandsValidationError, OpenHandsConflictError):
                raise
            except OpenHandsServerError:
                raise
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    delay = min(self._backoff_base ** attempt, self._backoff_max)
                    await asyncio.sleep(delay)
                    continue
                raise OpenHandsError(
                    f"Connection failed after {self._max_retries} retries: {exc}",
                    detail=str(exc),
                ) from exc

        raise OpenHandsError(
            f"Request failed after {self._max_retries} retries",
            detail=str(last_exc) if last_exc else "Unknown error",
        )

    @staticmethod
    def _extract_detail(resp: httpx.Response) -> str:
        """Extract error detail from an HTTP response."""
        try:
            data = resp.json()
            return data.get("detail", data.get("message", resp.text[:500]))
        except Exception:
            return resp.text[:500]

    # ------------------------------------------------------------------
    # Task operations
    # ------------------------------------------------------------------

    async def create_task(
        self,
        task_type: str,
        description: str,
        repository: str,
        branch: str = "main",
        target_language: str = "python",
        framework: Optional[str] = None,
        complexity: str = "medium",
        spec: Optional[str] = None,
        referenced_files: Optional[list[str]] = None,
        requirements: Optional[list[str]] = None,
        constraints: Optional[list[str]] = None,
        timeout: Optional[float] = None,
    ) -> Task:
        """Create a new coding task and start the lifecycle pipeline.

        Args:
            task_type: Type of task (feature-build, bug-fix, refactor, test-gen).
            description: Detailed task description (min 10 chars).
            repository: Target repository name.
            branch: Base branch to work from (default: main).
            target_language: Primary programming language (default: python).
            framework: Optional framework name (e.g., fastapi, react).
            complexity: Task complexity (low, medium, high, critical).
            spec: Optional pre-written specification.
            referenced_files: Files to reference for context.
            requirements: Functional requirements list.
            constraints: Implementation constraints list.
            timeout: Optional timeout override for this request.

        Returns:
            Task object with task_id, status, and metadata.

        Raises:
            OpenHandsValidationError: If required fields are missing or invalid.
            OpenHandsError: If task creation fails.
        """
        payload: dict[str, Any] = {
            "task_type": task_type,
            "description": description,
            "repository": repository,
            "branch": branch,
            "target_language": target_language,
            "complexity": complexity,
            "referenced_files": referenced_files or [],
            "requirements": requirements or [],
            "constraints": constraints or [],
        }
        if framework is not None:
            payload["framework"] = framework
        if spec is not None:
            payload["spec"] = spec

        resp = await self._request("POST", "/tasks", json=payload, timeout=timeout)
        return Task.model_validate(resp.json())

    async def get_task(self, task_id: str, timeout: Optional[float] = None) -> TaskDetail:
        """Get detailed information about a specific task.

        Args:
            task_id: The unique task identifier.
            timeout: Optional timeout override.

        Returns:
            TaskDetail with full lifecycle data.

        Raises:
            OpenHandsNotFoundError: If the task does not exist.
        """
        resp = await self._request("GET", f"/tasks/{task_id}", timeout=timeout)
        return TaskDetail.model_validate(resp.json())

    async def list_tasks(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        repository: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        timeout: Optional[float] = None,
    ) -> TaskListResponse:
        """List tasks with optional filters.

        Args:
            status: Filter by task status.
            task_type: Filter by task type.
            repository: Filter by repository name.
            limit: Maximum number of results (1-200, default 50).
            offset: Pagination offset (default 0).
            timeout: Optional timeout override.

        Returns:
            TaskListResponse with total count and task summaries.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if task_type is not None:
            params["task_type"] = task_type
        if repository is not None:
            params["repository"] = repository

        resp = await self._request("GET", "/tasks", params=params, timeout=timeout)
        return TaskListResponse.model_validate(resp.json())

    async def approve_task(
        self,
        task_id: str,
        feedback: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> TaskActionResponse:
        """Approve a task that is pending human review.

        This resumes the pipeline from the coding stage.

        Args:
            task_id: The unique task identifier.
            feedback: Optional feedback for the coding agent.
            timeout: Optional timeout override.

        Returns:
            TaskActionResponse confirming approval.

        Raises:
            OpenHandsNotFoundError: If the task does not exist.
            OpenHandsConflictError: If the task is not in pending_human_review status.
        """
        payload: dict[str, Any] = {}
        if feedback is not None:
            payload["feedback"] = feedback

        resp = await self._request("POST", f"/tasks/{task_id}/approve", json=payload, timeout=timeout)
        return TaskActionResponse.model_validate(resp.json())

    async def reject_task(
        self,
        task_id: str,
        feedback: str,
        timeout: Optional[float] = None,
    ) -> TaskActionResponse:
        """Reject a task that is pending human review.

        This marks the task as failed with the provided feedback.

        Args:
            task_id: The unique task identifier.
            feedback: Reason for rejection (min 5 chars).
            timeout: Optional timeout override.

        Returns:
            TaskActionResponse confirming rejection.

        Raises:
            OpenHandsNotFoundError: If the task does not exist.
            OpenHandsConflictError: If the task is not in a rejectable status.
            OpenHandsValidationError: If feedback is too short.
        """
        resp = await self._request(
            "POST",
            f"/tasks/{task_id}/reject",
            json={"feedback": feedback},
            timeout=timeout,
        )
        return TaskActionResponse.model_validate(resp.json())

    async def cancel_task(
        self,
        task_id: str,
        timeout: Optional[float] = None,
    ) -> TaskActionResponse:
        """Cancel an active task.

        Args:
            task_id: The unique task identifier.
            timeout: Optional timeout override.

        Returns:
            TaskActionResponse confirming cancellation.

        Raises:
            OpenHandsNotFoundError: If the task does not exist.
            OpenHandsConflictError: If the task is already complete or cancelled.
        """
        resp = await self._request("DELETE", f"/tasks/{task_id}", timeout=timeout)
        return TaskActionResponse.model_validate(resp.json())

    async def get_task_logs(
        self,
        task_id: str,
        timeout: Optional[float] = None,
    ) -> str:
        """Get execution logs for a task as a single string.

        Args:
            task_id: The unique task identifier.
            timeout: Optional timeout override.

        Returns:
            Concatenated log entries as a string.

        Raises:
            OpenHandsNotFoundError: If the task does not exist.
        """
        resp = await self._request("GET", f"/tasks/{task_id}/logs", timeout=timeout)
        data = TaskLogsResponse.model_validate(resp.json())
        return data.logs

    async def get_task_artifacts(
        self,
        task_id: str,
        timeout: Optional[float] = None,
    ) -> list[Artifact]:
        """Get artifacts produced by a task.

        Args:
            task_id: The unique task identifier.
            timeout: Optional timeout override.

        Returns:
            List of Artifact objects.

        Raises:
            OpenHandsNotFoundError: If the task does not exist.
        """
        resp = await self._request("GET", f"/tasks/{task_id}/artifacts", timeout=timeout)
        data = TaskArtifactsResponse.model_validate(resp.json())
        return data.artifacts

    async def health(self, timeout: Optional[float] = 5.0) -> HealthResponse:
        """Check the health of the task orchestrator.

        Args:
            timeout: Health check timeout (default: 5 seconds).

        Returns:
            HealthResponse with status information.
        """
        resp = await self._request("GET", "/health", timeout=timeout)
        return HealthResponse.model_validate(resp.json())

    async def wait_for_completion(
        self,
        task_id: str,
        poll_interval: float = 10.0,
        max_wait: float = 3600.0,
        terminal_statuses: Optional[set[str]] = None,
    ) -> TaskDetail:
        """Poll a task until it reaches a terminal status.

        Args:
            task_id: The unique task identifier.
            poll_interval: Seconds between polls (default: 10).
            max_wait: Maximum total wait time in seconds (default: 3600).
            terminal_statuses: Set of statuses considered terminal.

        Returns:
            TaskDetail when the task reaches a terminal status.

        Raises:
            TimeoutError: If max_wait is exceeded.
            OpenHandsNotFoundError: If the task does not exist.
        """
        if terminal_statuses is None:
            terminal_statuses = {"complete", "failed", "cancelled", "pending_human_review"}

        elapsed = 0.0
        while elapsed < max_wait:
            task = await self.get_task(task_id)
            if task.status in terminal_statuses:
                return task
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"Task {task_id} did not reach terminal status within {max_wait}s"
        )
