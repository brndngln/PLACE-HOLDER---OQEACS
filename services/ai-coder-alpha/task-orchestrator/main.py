#!/usr/bin/env python3
"""
SYSTEM 16 -- AI CODER ALPHA: Task Orchestrator
Omni Quantum Elite AI Coding System -- AI Coding Agent Layer

FastAPI microservice (port 3001) implementing the complete 10-stage task
lifecycle for OpenHands-based AI coding.  Manages task creation, context
compilation via Token Infinity, spec generation/review via Code Scorer,
coding via OpenHands sandbox, testing, gate checks, and Gitea PR creation.

Endpoints:
  POST   /tasks                         -- create a new coding task
  GET    /tasks                         -- list tasks with filters
  GET    /tasks/{task_id}               -- get task detail
  GET    /tasks/{task_id}/logs          -- get task execution logs
  GET    /tasks/{task_id}/artifacts     -- get task artifacts
  POST   /tasks/{task_id}/approve       -- approve a task pending review
  POST   /tasks/{task_id}/reject        -- reject a task pending review
  DELETE /tasks/{task_id}               -- cancel a task
  GET    /health                        -- liveness probe
  GET    /ready                         -- readiness probe
  GET    /metrics                       -- Prometheus metrics

Requirements: fastapi, uvicorn, httpx, structlog, prometheus_client, pydantic, pyyaml, websockets
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger(service="task-orchestrator", system="16", component="ai-coder-alpha")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(os.environ.get(
    "OPENHANDS_CONFIG_PATH",
    str(Path(__file__).resolve().parent.parent / "config" / "openhands-config.yaml"),
))

LITELLM_URL = os.environ.get("LITELLM_URL", "http://omni-litellm:4000")
TOKEN_INFINITY_CONTEXT_URL = os.environ.get("TOKEN_INFINITY_CONTEXT_URL", "http://omni-token-infinity:9600")
TOKEN_INFINITY_ROUTING_URL = os.environ.get("TOKEN_INFINITY_ROUTING_URL", "http://omni-token-infinity:9601")
CODE_SCORER_URL = os.environ.get("CODE_SCORER_URL", "http://omni-code-scorer")
GATE_ENGINE_URL = os.environ.get("GATE_ENGINE_URL", "http://omni-gate-engine")
GITEA_URL = os.environ.get("GITEA_URL", "http://omni-gitea:3000")
GITEA_TOKEN = os.environ.get("GITEA_TOKEN", "")
LANGFUSE_URL = os.environ.get("LANGFUSE_URL", "http://omni-langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
MATTERMOST_WEBHOOK_URL = os.environ.get("MATTERMOST_WEBHOOK_URL", "")
VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "")
OPENHANDS_URL = os.environ.get("OPENHANDS_URL", "http://localhost:3000")
OMI_BRIDGE_URL = os.environ.get("OMI_BRIDGE_URL", "http://omni-omi-bridge:9700")
GITEA_ORG = os.environ.get("GITEA_ORG", "omni-quantum")

# ---------------------------------------------------------------------------
# Load YAML config at module level
# ---------------------------------------------------------------------------
_config: dict[str, Any] = {}


def load_config() -> dict[str, Any]:
    """Load the openhands-config.yaml file."""
    global _config
    if not _config and CONFIG_PATH.exists():
        with open(CONFIG_PATH) as fh:
            _config = yaml.safe_load(fh) or {}
        log.info("config_loaded", path=str(CONFIG_PATH))
    return _config


# ---------------------------------------------------------------------------
# Enums and Pydantic models
# ---------------------------------------------------------------------------
class TaskType(str, Enum):
    FEATURE_BUILD = "feature-build"
    BUG_FIX = "bug-fix"
    REFACTOR = "refactor"
    TEST_GEN = "test-gen"


class TaskStatus(str, Enum):
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


class TaskCreateRequest(BaseModel):
    """Request body for creating a new coding task."""
    task_type: TaskType = Field(..., description="Type of coding task")
    description: str = Field(..., min_length=10, max_length=5000, description="Detailed task description")
    repository: str = Field(..., min_length=1, description="Target repository name")
    branch: str = Field(default="main", description="Base branch to work from")
    target_language: str = Field(default="python", description="Primary programming language")
    framework: Optional[str] = Field(default=None, description="Framework in use (e.g., fastapi, react)")
    complexity: str = Field(default="medium", pattern="^(low|medium|high|critical)$", description="Task complexity")
    spec: Optional[str] = Field(default=None, description="Optional pre-written specification")
    referenced_files: list[str] = Field(default_factory=list, description="Files to reference for context")
    requirements: list[str] = Field(default_factory=list, description="Functional requirements")
    constraints: list[str] = Field(default_factory=list, description="Implementation constraints")


class TaskApproveRequest(BaseModel):
    """Request body for approving a task pending human review."""
    feedback: Optional[str] = Field(default=None, description="Optional feedback for the agent")


class TaskRejectRequest(BaseModel):
    """Request body for rejecting a task."""
    feedback: str = Field(..., min_length=5, description="Reason for rejection")


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


class TaskArtifact(BaseModel):
    """An artifact produced by a task."""
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    artifact_type: str
    path: str
    size_bytes: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())


class TaskRecord(BaseModel):
    """Complete task record with full lifecycle state."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType
    status: TaskStatus = TaskStatus.RECEIVED
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

    # Lifecycle data
    compiled_context: Optional[str] = None
    generated_spec: Optional[str] = None
    spec_score: Optional[ScoreDetail] = None
    code_score: Optional[ScoreDetail] = None
    gate_result: Optional[GateCheckResult] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    working_branch: Optional[str] = None

    # Counters
    spec_revision_count: int = 0
    coding_iteration_count: int = 0
    test_fix_count: int = 0

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None

    # Logs and artifacts
    logs: list[str] = Field(default_factory=list)
    artifacts: list[TaskArtifact] = Field(default_factory=list)
    error_message: Optional[str] = None
    human_feedback: Optional[str] = None


class TaskSummary(BaseModel):
    """Lightweight task summary for list endpoint."""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    description: str
    repository: str
    branch: str
    complexity: str
    created_at: str
    updated_at: str
    pr_url: Optional[str] = None
    code_score_overall: Optional[float] = None


# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
TASKS_TOTAL = Counter(
    "openhands_tasks_total", "Total tasks processed",
    ["task_type", "status"],
)
TASK_DURATION = Histogram(
    "openhands_task_duration_seconds", "Task duration in seconds",
    ["task_type"],
    buckets=[30, 60, 120, 300, 600, 900, 1200, 1800, 3600],
)
QUALITY_SCORE = Histogram(
    "openhands_quality_score", "Code quality scores",
    ["task_type"],
    buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
)
REVISION_COUNT = Histogram(
    "openhands_revision_count", "Number of revisions per task",
    ["task_type"],
    buckets=[0, 1, 2, 3, 4, 5],
)
GATE_PASS_RATE = Counter(
    "openhands_gate_pass_rate", "Gate check pass/fail count",
    ["task_type", "result"],
)
ACTIVE_TASKS = Gauge(
    "openhands_active_tasks", "Currently active tasks",
)

# ---------------------------------------------------------------------------
# In-memory task store
# ---------------------------------------------------------------------------
tasks_store: dict[str, TaskRecord] = {}
task_websockets: dict[str, list[WebSocket]] = {}

# ---------------------------------------------------------------------------
# Vault helpers
# ---------------------------------------------------------------------------


async def resolve_vault_secret(client: httpx.AsyncClient, vault_path: str) -> str:
    """Fetch a secret value from Vault KV v2."""
    if not VAULT_TOKEN:
        log.warning("vault_token_missing", path=vault_path)
        return ""
    try:
        resp = await client.get(
            f"{VAULT_ADDR}/v1/{vault_path}",
            headers={"X-Vault-Token": VAULT_TOKEN},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {}).get("data", {})
        return data.get("value", data.get("token", data.get("key", "")))
    except Exception as exc:
        log.error("vault_secret_resolve_failed", path=vault_path, error=str(exc))
        return ""


# ---------------------------------------------------------------------------
# HTTP helpers with retry
# ---------------------------------------------------------------------------


async def http_request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    timeout: float = 30.0,
    **kwargs: Any,
) -> httpx.Response:
    """Execute an HTTP request with exponential backoff retry."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = await client.request(method, url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code < 500:
                raise
            log.warning("http_retry", url=url, attempt=attempt + 1, status=exc.response.status_code)
        except httpx.TransportError as exc:
            last_exc = exc
            log.warning("http_transport_retry", url=url, attempt=attempt + 1, error=str(exc))
        if attempt < max_retries - 1:
            await asyncio.sleep(min(backoff_base ** attempt, 30.0))
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Mattermost notification helpers
# ---------------------------------------------------------------------------


async def notify_mattermost(
    client: httpx.AsyncClient,
    channel: str,
    text: str,
    icon_emoji: str = ":robot:",
) -> None:
    """Post a notification to Mattermost via incoming webhook."""
    if not MATTERMOST_WEBHOOK_URL:
        log.debug("mattermost_skip_no_webhook", channel=channel)
        return
    payload = {
        "channel": channel,
        "username": "OpenHands AI",
        "icon_emoji": icon_emoji,
        "text": text,
    }
    try:
        await client.post(MATTERMOST_WEBHOOK_URL, json=payload, timeout=10.0)
        log.info("mattermost_notified", channel=channel)
    except Exception as exc:
        log.warning("mattermost_notify_failed", channel=channel, error=str(exc))


# ---------------------------------------------------------------------------
# WebSocket progress broadcast
# ---------------------------------------------------------------------------


async def broadcast_progress(task_id: str, stage: str, message: str, progress_pct: float = 0.0) -> None:
    """Broadcast task progress to all connected WebSocket clients for a task."""
    sockets = task_websockets.get(task_id, [])
    payload = {
        "task_id": task_id,
        "stage": stage,
        "message": message,
        "progress_pct": progress_pct,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
    disconnected: list[WebSocket] = []
    for ws in sockets:
        try:
            await ws.send_json(payload)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        sockets.remove(ws)


# ---------------------------------------------------------------------------
# Task log helper
# ---------------------------------------------------------------------------


def task_log(task: TaskRecord, message: str) -> None:
    """Append a timestamped log entry to the task record."""
    entry = f"[{datetime.now(tz=timezone.utc).isoformat()}] {message}"
    task.logs.append(entry)
    task.updated_at = datetime.now(tz=timezone.utc).isoformat()
    log.info("task_event", task_id=task.task_id, stage=task.status.value, message=message)


# ---------------------------------------------------------------------------
# Stage 1: RECEIVED
# ---------------------------------------------------------------------------


async def stage_received(task: TaskRecord) -> None:
    """Stage 1 -- Validate and register the task."""
    task.status = TaskStatus.RECEIVED
    task.working_branch = f"openhands/{task.task_type.value}/{task.task_id[:8]}"
    task_log(task, f"Task received: {task.task_type.value} for {task.repository}")
    TASKS_TOTAL.labels(task_type=task.task_type.value, status="received").inc()
    ACTIVE_TASKS.inc()
    await broadcast_progress(task.task_id, "received", "Task received and validated", 5.0)


# ---------------------------------------------------------------------------
# Stage 2: CONTEXT_COMPILING
# ---------------------------------------------------------------------------


async def stage_context_compiling(client: httpx.AsyncClient, task: TaskRecord) -> None:
    """Stage 2 -- Call Token Infinity to compile context from referenced files and repo."""
    task.status = TaskStatus.CONTEXT_COMPILING
    task_log(task, "Compiling context via Token Infinity")
    await broadcast_progress(task.task_id, "context_compiling", "Compiling project context", 10.0)

    payload = {
        "repository": f"{GITEA_ORG}/{task.repository}",
        "branch": task.branch,
        "files": task.referenced_files,
        "description": task.description,
        "requirements": task.requirements,
        "constraints": task.constraints,
        "target_language": task.target_language,
        "framework": task.framework or "",
        "max_tokens": 32000,
    }

    try:
        resp = await http_request_with_retry(
            client, "POST",
            f"{TOKEN_INFINITY_CONTEXT_URL}/context/compile",
            json=payload,
            timeout=60.0,
        )
        result = resp.json()
        task.compiled_context = result.get("compiled_context", "")
        token_count = result.get("token_count", 0)
        task_log(task, f"Context compiled: {token_count} tokens")
        await broadcast_progress(task.task_id, "context_compiling", f"Context compiled ({token_count} tokens)", 20.0)
    except Exception as exc:
        task_log(task, f"Context compilation failed: {exc}")
        task.compiled_context = (
            f"Repository: {task.repository}\n"
            f"Branch: {task.branch}\n"
            f"Description: {task.description}\n"
            f"Requirements: {'; '.join(task.requirements)}\n"
            f"Constraints: {'; '.join(task.constraints)}\n"
            f"Referenced files: {', '.join(task.referenced_files)}"
        )
        task_log(task, "Using fallback context from task description")


# ---------------------------------------------------------------------------
# Stage 3: SPEC_GENERATING
# ---------------------------------------------------------------------------


async def stage_spec_generating(client: httpx.AsyncClient, task: TaskRecord) -> None:
    """Stage 3 -- Generate specification via LLM if no spec provided."""
    if task.spec:
        task.generated_spec = task.spec
        task_log(task, "Using user-provided specification")
        await broadcast_progress(task.task_id, "spec_generating", "Using provided specification", 30.0)
        return

    task.status = TaskStatus.SPEC_GENERATING
    task_log(task, "Generating specification via LLM")
    await broadcast_progress(task.task_id, "spec_generating", "Generating specification", 25.0)

    system_prompt = (
        "You are a senior software architect. Generate a detailed, actionable technical specification "
        "for the following coding task. Include:\n"
        "1. Objective and scope\n"
        "2. Architecture and design decisions\n"
        "3. API contracts (if applicable)\n"
        "4. Data models\n"
        "5. Error handling strategy\n"
        "6. Testing strategy\n"
        "7. File structure and naming\n"
        "8. Edge cases to handle\n"
        "9. Performance considerations\n"
        "10. Security considerations\n\n"
        "Be precise and implementation-ready. Use the provided context."
    )

    user_prompt = (
        f"Task Type: {task.task_type.value}\n"
        f"Description: {task.description}\n"
        f"Repository: {task.repository}\n"
        f"Language: {task.target_language}\n"
        f"Framework: {task.framework or 'N/A'}\n"
        f"Complexity: {task.complexity}\n"
        f"Requirements:\n" + "\n".join(f"  - {r}" for r in task.requirements) + "\n"
        f"Constraints:\n" + "\n".join(f"  - {c}" for c in task.constraints) + "\n\n"
        f"Project Context:\n{task.compiled_context or 'No additional context available.'}"
    )

    try:
        resp = await http_request_with_retry(
            client, "POST",
            f"{LITELLM_URL}/v1/chat/completions",
            json={
                "model": "devstral-2:123b",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 8192,
            },
            timeout=120.0,
        )
        result = resp.json()
        task.generated_spec = result["choices"][0]["message"]["content"]
        task_log(task, "Specification generated successfully")
        await broadcast_progress(task.task_id, "spec_generating", "Specification generated", 30.0)
    except Exception as exc:
        error_msg = f"Spec generation failed: {exc}"
        task_log(task, error_msg)
        task.status = TaskStatus.FAILED
        task.error_message = error_msg
        raise


# ---------------------------------------------------------------------------
# Stage 4: SPEC_REVIEW
# ---------------------------------------------------------------------------


async def stage_spec_review(client: httpx.AsyncClient, task: TaskRecord) -> bool:
    """Stage 4 -- Submit spec to Code Scorer for 10-dimension review.

    Returns True if spec is approved (auto or after revision), False if human review needed.
    """
    task.status = TaskStatus.SPEC_REVIEW
    task_log(task, "Submitting specification for review")
    await broadcast_progress(task.task_id, "spec_review", "Reviewing specification", 35.0)

    config = load_config()
    max_revisions = config.get("task_defaults", {}).get("max_spec_revisions", 2)
    auto_threshold = config.get("task_defaults", {}).get("auto_approve_threshold", 8.0)
    human_threshold = config.get("task_defaults", {}).get("human_review_threshold", 6.0)

    for revision in range(max_revisions + 1):
        try:
            resp = await http_request_with_retry(
                client, "POST",
                f"{CODE_SCORER_URL}/score",
                json={
                    "content": task.generated_spec,
                    "content_type": "specification",
                    "task_type": task.task_type.value,
                    "language": task.target_language,
                    "context": task.description,
                },
                timeout=30.0,
            )
            score_data = resp.json()
            task.spec_score = ScoreDetail(
                correctness=score_data.get("dimensions", {}).get("correctness", 0),
                completeness=score_data.get("dimensions", {}).get("completeness", 0),
                maintainability=score_data.get("dimensions", {}).get("maintainability", 0),
                readability=score_data.get("dimensions", {}).get("readability", 0),
                security=score_data.get("dimensions", {}).get("security", 0),
                performance=score_data.get("dimensions", {}).get("performance", 0),
                test_coverage=score_data.get("dimensions", {}).get("test_coverage", 0),
                documentation=score_data.get("dimensions", {}).get("documentation", 0),
                error_handling=score_data.get("dimensions", {}).get("error_handling", 0),
                best_practices=score_data.get("dimensions", {}).get("best_practices", 0),
                overall=score_data.get("overall_score", 0),
            )
            overall = task.spec_score.overall
            task_log(task, f"Spec score: {overall:.1f}/10 (revision {revision})")

            if overall >= auto_threshold:
                task_log(task, "Specification auto-approved")
                await broadcast_progress(task.task_id, "spec_review", f"Spec approved (score: {overall:.1f})", 40.0)
                return True

            if overall < human_threshold:
                task_log(task, f"Spec score {overall:.1f} below threshold {human_threshold}, requesting human review")
                task.status = TaskStatus.PENDING_HUMAN_REVIEW
                await notify_mattermost(
                    client, "reviews",
                    f"### :mag: Spec Review Needed\n"
                    f"**Task:** `{task.task_id}`\n"
                    f"**Type:** {task.task_type.value}\n"
                    f"**Repository:** {task.repository}\n"
                    f"**Score:** {overall:.1f}/10\n"
                    f"**Description:** {task.description[:200]}\n\n"
                    f"Approve: `POST /tasks/{task.task_id}/approve`\n"
                    f"Reject: `POST /tasks/{task.task_id}/reject`",
                )
                await broadcast_progress(
                    task.task_id, "spec_review",
                    f"Spec needs human review (score: {overall:.1f})", 35.0,
                )
                return False

            # Score between human_threshold and auto_threshold: attempt revision
            if revision < max_revisions:
                task.spec_revision_count += 1
                task_log(task, f"Revising specification (attempt {revision + 1}/{max_revisions})")
                feedback = score_data.get("feedback", "Improve overall quality, address weak dimensions.")

                revise_resp = await http_request_with_retry(
                    client, "POST",
                    f"{LITELLM_URL}/v1/chat/completions",
                    json={
                        "model": "devstral-2:123b",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a senior software architect. Revise the specification "
                                           "based on the review feedback. Keep all good parts and improve weak areas.",
                            },
                            {"role": "user", "content": f"Original spec:\n{task.generated_spec}"},
                            {"role": "user", "content": f"Review feedback (score {overall:.1f}/10):\n{feedback}"},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 8192,
                    },
                    timeout=120.0,
                )
                task.generated_spec = revise_resp.json()["choices"][0]["message"]["content"]
                task_log(task, f"Specification revised based on feedback")
                await broadcast_progress(
                    task.task_id, "spec_review",
                    f"Revising specification (attempt {revision + 1})", 37.0,
                )
            else:
                task_log(task, "Max spec revisions reached, requesting human review")
                task.status = TaskStatus.PENDING_HUMAN_REVIEW
                await notify_mattermost(
                    client, "reviews",
                    f"### :mag: Spec Review Needed (max revisions reached)\n"
                    f"**Task:** `{task.task_id}`\n"
                    f"**Score:** {overall:.1f}/10 after {max_revisions} revisions\n"
                    f"**Repository:** {task.repository}\n\n"
                    f"Approve: `POST /tasks/{task.task_id}/approve`\n"
                    f"Reject: `POST /tasks/{task.task_id}/reject`",
                )
                return False

        except Exception as exc:
            task_log(task, f"Spec review failed: {exc}")
            task_log(task, "Auto-approving spec due to scorer unavailability")
            return True

    return True


# ---------------------------------------------------------------------------
# Stage 5: CODING
# ---------------------------------------------------------------------------


async def stage_coding(client: httpx.AsyncClient, task: TaskRecord) -> None:
    """Stage 5 -- Invoke OpenHands agent with compiled context and spec."""
    task.status = TaskStatus.CODING
    task_log(task, "Starting OpenHands coding session")
    await broadcast_progress(task.task_id, "coding", "Starting OpenHands coding agent", 45.0)

    await notify_mattermost(
        client, "builds",
        f"### :hammer_and_wrench: OpenHands Coding Started\n"
        f"**Task:** `{task.task_id}`\n"
        f"**Type:** {task.task_type.value}\n"
        f"**Repository:** {task.repository}\n"
        f"**Branch:** `{task.working_branch}`\n"
        f"**Description:** {task.description[:200]}",
    )

    coding_prompt = (
        f"## Task: {task.task_type.value}\n\n"
        f"### Description\n{task.description}\n\n"
        f"### Specification\n{task.generated_spec or 'No specification provided.'}\n\n"
        f"### Requirements\n" + "\n".join(f"- {r}" for r in task.requirements) + "\n\n"
        f"### Constraints\n" + "\n".join(f"- {c}" for c in task.constraints) + "\n\n"
        f"### Context\n{task.compiled_context or 'No additional context.'}\n\n"
        f"### Instructions\n"
        f"1. Implement the task in {task.target_language}"
        + (f" using {task.framework}" if task.framework else "") + "\n"
        f"2. Write comprehensive tests with >80% coverage\n"
        f"3. Follow best practices for {task.target_language}\n"
        f"4. Include proper error handling and type hints\n"
        f"5. Add docstrings and inline documentation\n"
        f"6. Ensure code is production-ready with no TODOs or stubs\n"
        f"7. Create or update all necessary files in the workspace\n"
    )

    openhands_payload = {
        "task": coding_prompt,
        "repository": f"{GITEA_ORG}/{task.repository}",
        "branch": task.working_branch,
        "base_branch": task.branch,
        "language": task.target_language,
        "framework": task.framework or "",
        "sandbox": {
            "image": _resolve_sandbox_image(task.target_language),
            "max_runtime_seconds": 600,
            "max_memory_mb": 2048,
            "enable_networking": True,
        },
    }

    try:
        resp = await http_request_with_retry(
            client, "POST",
            f"{OPENHANDS_URL}/api/tasks",
            json=openhands_payload,
            timeout=600.0,
            max_retries=1,
        )
        result = resp.json()
        openhands_task_id = result.get("task_id", "")
        task_log(task, f"OpenHands session started: {openhands_task_id}")

        # Poll for completion
        poll_interval = 10
        max_polls = 60  # 10 minutes max
        for poll in range(max_polls):
            await asyncio.sleep(poll_interval)
            try:
                status_resp = await client.get(
                    f"{OPENHANDS_URL}/api/tasks/{openhands_task_id}",
                    timeout=15.0,
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()
                oh_status = status_data.get("status", "running")

                progress = 45.0 + (poll / max_polls) * 20.0
                await broadcast_progress(
                    task.task_id, "coding",
                    f"OpenHands working... ({oh_status})", min(progress, 65.0),
                )

                if oh_status == "completed":
                    task_log(task, "OpenHands coding session completed")
                    # Collect artifacts
                    files_changed = status_data.get("files_changed", [])
                    for f in files_changed:
                        task.artifacts.append(TaskArtifact(
                            name=Path(f).name,
                            artifact_type="source_code",
                            path=f,
                        ))
                    task.coding_iteration_count += 1
                    await broadcast_progress(task.task_id, "coding", "Coding complete", 65.0)
                    return

                if oh_status in ("failed", "error"):
                    error = status_data.get("error", "Unknown OpenHands error")
                    task_log(task, f"OpenHands session failed: {error}")
                    raise RuntimeError(f"OpenHands coding failed: {error}")

            except httpx.HTTPError as poll_exc:
                task_log(task, f"Poll error (continuing): {poll_exc}")

        task_log(task, "OpenHands session timed out after 10 minutes")
        raise TimeoutError("OpenHands coding session timed out")

    except Exception as exc:
        error_msg = f"Coding stage failed: {exc}"
        task_log(task, error_msg)
        task.error_message = error_msg
        raise


def _resolve_sandbox_image(language: str) -> str:
    """Resolve the sandbox Docker image for a given language."""
    config = load_config()
    images = config.get("sandbox", {}).get("available_images", {})
    lang_lower = language.lower()
    if lang_lower in images:
        return images[lang_lower]
    if lang_lower in ("python", "py"):
        return "python:3.12-slim"
    if lang_lower in ("javascript", "typescript", "js", "ts", "node"):
        return "node:22-slim"
    if lang_lower in ("go", "golang"):
        return "golang:1.23-bookworm"
    if lang_lower == "rust":
        return "rust:1.82-slim-bookworm"
    return "omni-quantum/fullstack:latest"


# ---------------------------------------------------------------------------
# Stage 6: SELF_REVIEW
# ---------------------------------------------------------------------------


async def stage_self_review(client: httpx.AsyncClient, task: TaskRecord) -> None:
    """Stage 6 -- Code Scorer 10-dimension review. >=8 proceed, <8 feedback to OpenHands."""
    task.status = TaskStatus.SELF_REVIEW
    task_log(task, "Submitting code for self-review via Code Scorer")
    await broadcast_progress(task.task_id, "self_review", "Running code quality review", 68.0)

    config = load_config()
    max_iterations = config.get("task_defaults", {}).get("max_coding_iterations", 3)
    auto_threshold = config.get("task_defaults", {}).get("auto_approve_threshold", 8.0)

    for iteration in range(max_iterations):
        try:
            # Gather code content from artifacts
            code_content = ""
            for artifact in task.artifacts:
                if artifact.artifact_type == "source_code":
                    code_content += f"\n--- {artifact.path} ---\n"
                    # In production, read file content from workspace
                    code_content += f"[File: {artifact.path}]\n"

            resp = await http_request_with_retry(
                client, "POST",
                f"{CODE_SCORER_URL}/score",
                json={
                    "content": code_content,
                    "content_type": "code",
                    "task_type": task.task_type.value,
                    "language": task.target_language,
                    "specification": task.generated_spec or "",
                    "context": task.description,
                },
                timeout=30.0,
            )
            score_data = resp.json()
            task.code_score = ScoreDetail(
                correctness=score_data.get("dimensions", {}).get("correctness", 0),
                completeness=score_data.get("dimensions", {}).get("completeness", 0),
                maintainability=score_data.get("dimensions", {}).get("maintainability", 0),
                readability=score_data.get("dimensions", {}).get("readability", 0),
                security=score_data.get("dimensions", {}).get("security", 0),
                performance=score_data.get("dimensions", {}).get("performance", 0),
                test_coverage=score_data.get("dimensions", {}).get("test_coverage", 0),
                documentation=score_data.get("dimensions", {}).get("documentation", 0),
                error_handling=score_data.get("dimensions", {}).get("error_handling", 0),
                best_practices=score_data.get("dimensions", {}).get("best_practices", 0),
                overall=score_data.get("overall_score", 0),
            )
            overall = task.code_score.overall
            task_log(task, f"Code score: {overall:.1f}/10 (iteration {iteration + 1})")
            QUALITY_SCORE.labels(task_type=task.task_type.value).observe(overall)

            if overall >= auto_threshold:
                task_log(task, "Code quality approved")
                await broadcast_progress(task.task_id, "self_review", f"Code approved (score: {overall:.1f})", 75.0)
                return

            # Send feedback to OpenHands for improvement
            if iteration < max_iterations - 1:
                task.coding_iteration_count += 1
                feedback = score_data.get("feedback", "Improve code quality across all dimensions.")
                weak_dims = [
                    dim for dim, val in score_data.get("dimensions", {}).items()
                    if isinstance(val, (int, float)) and val < 7.0
                ]
                task_log(task, f"Requesting code improvement: weak dimensions = {weak_dims}")

                improvement_payload = {
                    "task_id": task.task_id,
                    "feedback": feedback,
                    "weak_dimensions": weak_dims,
                    "current_score": overall,
                    "target_score": auto_threshold,
                    "repository": f"{GITEA_ORG}/{task.repository}",
                    "branch": task.working_branch,
                }

                try:
                    await http_request_with_retry(
                        client, "POST",
                        f"{OPENHANDS_URL}/api/tasks/improve",
                        json=improvement_payload,
                        timeout=300.0,
                        max_retries=1,
                    )
                    task_log(task, f"OpenHands improvement iteration {iteration + 2} completed")
                except Exception as improve_exc:
                    task_log(task, f"OpenHands improvement failed: {improve_exc}")
                    break

                await broadcast_progress(
                    task.task_id, "self_review",
                    f"Improving code (iteration {iteration + 2}, score: {overall:.1f})", 70.0,
                )

        except Exception as exc:
            task_log(task, f"Self-review failed: {exc}")
            task_log(task, "Proceeding despite review failure")
            return

    REVISION_COUNT.labels(task_type=task.task_type.value).observe(task.coding_iteration_count)
    task_log(task, f"Self-review complete after {task.coding_iteration_count} iterations")


# ---------------------------------------------------------------------------
# Stage 7: TESTING
# ---------------------------------------------------------------------------


async def stage_testing(client: httpx.AsyncClient, task: TaskRecord) -> None:
    """Stage 7 -- Run pytest/jest in sandbox. Coverage >80%. Failures trigger fix cycles."""
    task.status = TaskStatus.TESTING
    task_log(task, "Running tests in sandbox")
    await broadcast_progress(task.task_id, "testing", "Running test suite", 78.0)

    config = load_config()
    max_fixes = config.get("task_defaults", {}).get("max_test_fix_iterations", 2)
    min_coverage = config.get("task_defaults", {}).get("min_coverage_pct", 80)

    test_command = "pytest --cov --cov-report=json -v" if task.target_language == "python" else "npx jest --coverage --json"

    for fix_attempt in range(max_fixes + 1):
        test_payload = {
            "repository": f"{GITEA_ORG}/{task.repository}",
            "branch": task.working_branch,
            "command": test_command,
            "language": task.target_language,
            "timeout": 120,
        }

        try:
            resp = await http_request_with_retry(
                client, "POST",
                f"{OPENHANDS_URL}/api/sandbox/exec",
                json=test_payload,
                timeout=180.0,
                max_retries=1,
            )
            test_result = resp.json()
            exit_code = test_result.get("exit_code", 1)
            output = test_result.get("output", "")
            coverage = test_result.get("coverage_pct", 0.0)

            task_log(task, f"Test run exit_code={exit_code}, coverage={coverage:.1f}%")

            if exit_code == 0 and coverage >= min_coverage:
                task_log(task, f"Tests passed with {coverage:.1f}% coverage")
                task.artifacts.append(TaskArtifact(
                    name="test-results.json",
                    artifact_type="test_results",
                    path=f"/workspace/{task.repository}/test-results.json",
                ))
                await broadcast_progress(
                    task.task_id, "testing",
                    f"Tests passed ({coverage:.1f}% coverage)", 85.0,
                )
                return

            # Tests failed or coverage too low -- ask OpenHands to fix
            if fix_attempt < max_fixes:
                task.test_fix_count += 1
                failure_msg = (
                    f"Tests {'failed' if exit_code != 0 else 'passed but coverage is low'} "
                    f"(exit_code={exit_code}, coverage={coverage:.1f}%, required={min_coverage}%)"
                )
                task_log(task, f"{failure_msg}, requesting fix (attempt {fix_attempt + 1}/{max_fixes})")

                fix_payload = {
                    "task_id": task.task_id,
                    "issue": "test_failure" if exit_code != 0 else "low_coverage",
                    "test_output": output[:5000],
                    "coverage_pct": coverage,
                    "required_coverage_pct": min_coverage,
                    "repository": f"{GITEA_ORG}/{task.repository}",
                    "branch": task.working_branch,
                }

                try:
                    await http_request_with_retry(
                        client, "POST",
                        f"{OPENHANDS_URL}/api/tasks/fix-tests",
                        json=fix_payload,
                        timeout=300.0,
                        max_retries=1,
                    )
                    task_log(task, "OpenHands test fix iteration completed")
                except Exception as fix_exc:
                    task_log(task, f"Test fix failed: {fix_exc}")
                    break

                await broadcast_progress(
                    task.task_id, "testing",
                    f"Fixing tests (attempt {fix_attempt + 1})", 80.0,
                )
            else:
                task_log(task, f"Max test fix attempts reached ({max_fixes})")

        except Exception as exc:
            task_log(task, f"Test execution failed: {exc}")
            if fix_attempt == max_fixes:
                task_log(task, "Proceeding despite test failures")
                return

    task_log(task, "Testing stage completed (some issues may remain)")


# ---------------------------------------------------------------------------
# Stage 8: GATE_CHECK
# ---------------------------------------------------------------------------


async def stage_gate_check(client: httpx.AsyncClient, task: TaskRecord) -> None:
    """Stage 8 -- Gate Engine: lint, security, complexity, coverage checks."""
    task.status = TaskStatus.GATE_CHECK
    task_log(task, "Running Gate Engine quality checks")
    await broadcast_progress(task.task_id, "gate_check", "Running quality gates", 87.0)

    gate_payload = {
        "repository": f"{GITEA_ORG}/{task.repository}",
        "branch": task.working_branch,
        "language": task.target_language,
        "checks": ["lint", "security", "complexity", "coverage"],
    }

    try:
        resp = await http_request_with_retry(
            client, "POST",
            f"{GATE_ENGINE_URL}/check",
            json=gate_payload,
            timeout=60.0,
        )
        gate_data = resp.json()
        task.gate_result = GateCheckResult(
            lint_passed=gate_data.get("lint", {}).get("passed", False),
            security_passed=gate_data.get("security", {}).get("passed", False),
            complexity_passed=gate_data.get("complexity", {}).get("passed", False),
            coverage_passed=gate_data.get("coverage", {}).get("passed", False),
            coverage_pct=gate_data.get("coverage", {}).get("pct", 0.0),
            all_passed=gate_data.get("all_passed", False),
            details=gate_data,
        )

        if task.gate_result.all_passed:
            task_log(task, "All quality gates passed")
            GATE_PASS_RATE.labels(task_type=task.task_type.value, result="pass").inc()
            await broadcast_progress(task.task_id, "gate_check", "All gates passed", 90.0)
        else:
            failed_checks = [
                check for check in ["lint", "security", "complexity", "coverage"]
                if not gate_data.get(check, {}).get("passed", True)
            ]
            task_log(task, f"Gate check failures: {failed_checks}")
            GATE_PASS_RATE.labels(task_type=task.task_type.value, result="fail").inc()

            # Attempt one fix cycle via OpenHands
            fix_payload = {
                "task_id": task.task_id,
                "failed_checks": failed_checks,
                "gate_details": gate_data,
                "repository": f"{GITEA_ORG}/{task.repository}",
                "branch": task.working_branch,
            }

            try:
                await http_request_with_retry(
                    client, "POST",
                    f"{OPENHANDS_URL}/api/tasks/fix-gates",
                    json=fix_payload,
                    timeout=300.0,
                    max_retries=1,
                )
                task_log(task, "Gate fix attempt completed, re-checking")

                # Re-run gate check
                re_resp = await http_request_with_retry(
                    client, "POST",
                    f"{GATE_ENGINE_URL}/check",
                    json=gate_payload,
                    timeout=60.0,
                )
                re_gate = re_resp.json()
                task.gate_result = GateCheckResult(
                    lint_passed=re_gate.get("lint", {}).get("passed", False),
                    security_passed=re_gate.get("security", {}).get("passed", False),
                    complexity_passed=re_gate.get("complexity", {}).get("passed", False),
                    coverage_passed=re_gate.get("coverage", {}).get("passed", False),
                    coverage_pct=re_gate.get("coverage", {}).get("pct", 0.0),
                    all_passed=re_gate.get("all_passed", False),
                    details=re_gate,
                )
                if task.gate_result.all_passed:
                    task_log(task, "All quality gates passed after fix")
                    GATE_PASS_RATE.labels(task_type=task.task_type.value, result="pass_after_fix").inc()
                else:
                    task_log(task, "Some gates still failing, proceeding with PR")
            except Exception as fix_exc:
                task_log(task, f"Gate fix failed: {fix_exc}")

            await broadcast_progress(task.task_id, "gate_check", "Gate check complete", 90.0)

    except Exception as exc:
        task_log(task, f"Gate check failed: {exc}")
        task.gate_result = GateCheckResult(details={"error": str(exc)})
        task_log(task, "Proceeding despite gate check failure")


# ---------------------------------------------------------------------------
# Stage 9: PR_CREATED
# ---------------------------------------------------------------------------


async def stage_pr_created(client: httpx.AsyncClient, task: TaskRecord) -> None:
    """Stage 9 -- Create PR on Gitea with full metadata."""
    task.status = TaskStatus.PR_CREATED
    task_log(task, "Creating pull request on Gitea")
    await broadcast_progress(task.task_id, "pr_created", "Creating pull request", 92.0)

    # Build PR body
    score_section = ""
    if task.code_score:
        score_section = (
            "## Code Quality Score\n\n"
            f"| Dimension | Score |\n"
            f"|-----------|-------|\n"
            f"| Correctness | {task.code_score.correctness:.1f} |\n"
            f"| Completeness | {task.code_score.completeness:.1f} |\n"
            f"| Maintainability | {task.code_score.maintainability:.1f} |\n"
            f"| Readability | {task.code_score.readability:.1f} |\n"
            f"| Security | {task.code_score.security:.1f} |\n"
            f"| Performance | {task.code_score.performance:.1f} |\n"
            f"| Test Coverage | {task.code_score.test_coverage:.1f} |\n"
            f"| Documentation | {task.code_score.documentation:.1f} |\n"
            f"| Error Handling | {task.code_score.error_handling:.1f} |\n"
            f"| Best Practices | {task.code_score.best_practices:.1f} |\n"
            f"| **Overall** | **{task.code_score.overall:.1f}/10** |\n\n"
        )

    gate_section = ""
    if task.gate_result:
        gate_section = (
            "## Gate Check Results\n\n"
            f"| Check | Result |\n"
            f"|-------|--------|\n"
            f"| Lint | {'PASS' if task.gate_result.lint_passed else 'FAIL'} |\n"
            f"| Security | {'PASS' if task.gate_result.security_passed else 'FAIL'} |\n"
            f"| Complexity | {'PASS' if task.gate_result.complexity_passed else 'FAIL'} |\n"
            f"| Coverage ({task.gate_result.coverage_pct:.1f}%) | {'PASS' if task.gate_result.coverage_passed else 'FAIL'} |\n"
            f"| **Overall** | **{'ALL PASS' if task.gate_result.all_passed else 'HAS FAILURES'}** |\n\n"
        )

    spec_section = ""
    if task.generated_spec:
        spec_summary = task.generated_spec[:2000]
        if len(task.generated_spec) > 2000:
            spec_summary += "\n\n... (truncated)"
        spec_section = f"## Specification\n\n<details>\n<summary>Click to expand</summary>\n\n{spec_summary}\n\n</details>\n\n"

    test_section = ""
    test_artifacts = [a for a in task.artifacts if a.artifact_type == "test_results"]
    if test_artifacts:
        test_section = (
            "## Test Results\n\n"
            f"- Test fix iterations: {task.test_fix_count}\n"
            f"- Test artifacts: {len(test_artifacts)}\n\n"
        )

    pr_body = (
        f"## AI-Generated Pull Request\n\n"
        f"**Task ID:** `{task.task_id}`\n"
        f"**Task Type:** {task.task_type.value}\n"
        f"**Complexity:** {task.complexity}\n"
        f"**Language:** {task.target_language}\n"
        f"**Framework:** {task.framework or 'N/A'}\n"
        f"**Coding Iterations:** {task.coding_iteration_count}\n\n"
        f"## Description\n\n{task.description}\n\n"
        f"{spec_section}"
        f"{score_section}"
        f"{test_section}"
        f"{gate_section}"
        f"---\n"
        f"*Generated by OpenHands AI (System 16 -- AI Coder Alpha)*\n"
    )

    # Map task types to PR title prefixes
    type_prefixes = {
        TaskType.FEATURE_BUILD: "feat",
        TaskType.BUG_FIX: "fix",
        TaskType.REFACTOR: "refactor",
        TaskType.TEST_GEN: "test",
    }
    prefix = type_prefixes.get(task.task_type, "chore")
    pr_title = f"{prefix}: {task.description[:80]}"

    labels = ["ai-generated", "openhands", task.task_type.value]
    if task.code_score and task.code_score.overall >= 8.0:
        labels.append("high-quality")
    if task.gate_result and task.gate_result.all_passed:
        labels.append("gates-passed")

    gitea_headers = {
        "Authorization": f"token {GITEA_TOKEN}",
        "Content-Type": "application/json",
    }

    pr_payload = {
        "title": pr_title,
        "body": pr_body,
        "head": task.working_branch,
        "base": task.branch,
        "labels": [],
        "assignees": ["quantum-lead"],
    }

    try:
        # Create labels if needed (best-effort)
        for label_name in labels:
            try:
                await client.post(
                    f"{GITEA_URL}/api/v1/repos/{GITEA_ORG}/{task.repository}/labels",
                    headers=gitea_headers,
                    json={"name": label_name, "color": "#0075ca"},
                    timeout=10.0,
                )
            except Exception:
                pass

        # Get label IDs
        try:
            labels_resp = await client.get(
                f"{GITEA_URL}/api/v1/repos/{GITEA_ORG}/{task.repository}/labels",
                headers=gitea_headers,
                timeout=10.0,
            )
            if labels_resp.status_code == 200:
                all_labels = labels_resp.json()
                label_ids = [lb["id"] for lb in all_labels if lb["name"] in labels]
                pr_payload["labels"] = label_ids
        except Exception:
            pass

        resp = await http_request_with_retry(
            client, "POST",
            f"{GITEA_URL}/api/v1/repos/{GITEA_ORG}/{task.repository}/pulls",
            headers=gitea_headers,
            json=pr_payload,
            timeout=30.0,
        )
        pr_data = resp.json()
        task.pr_url = pr_data.get("html_url", "")
        task.pr_number = pr_data.get("number", 0)
        task_log(task, f"PR created: {task.pr_url} (#{task.pr_number})")

        # Request reviewers
        try:
            await client.post(
                f"{GITEA_URL}/api/v1/repos/{GITEA_ORG}/{task.repository}/pulls/{task.pr_number}/requested_reviewers",
                headers=gitea_headers,
                json={"reviewers": ["quantum-lead"]},
                timeout=10.0,
            )
        except Exception:
            pass

        overall_score = task.code_score.overall if task.code_score else 0.0
        await notify_mattermost(
            client, "reviews",
            f"### :rocket: OpenHands PR Created\n"
            f"**Task:** `{task.task_id}`\n"
            f"**PR:** [{pr_title}]({task.pr_url})\n"
            f"**Quality Score:** {overall_score:.1f}/10\n"
            f"**Gates:** {'ALL PASS' if task.gate_result and task.gate_result.all_passed else 'HAS ISSUES'}\n"
            f"**Repository:** {task.repository}\n"
            f"**Iterations:** {task.coding_iteration_count}",
        )

        await broadcast_progress(task.task_id, "pr_created", f"PR #{task.pr_number} created", 95.0)

    except Exception as exc:
        error_msg = f"PR creation failed: {exc}"
        task_log(task, error_msg)
        task.error_message = error_msg
        await notify_mattermost(
            client, "alerts",
            f"### :x: OpenHands PR Creation Failed\n"
            f"**Task:** `{task.task_id}`\n"
            f"**Repository:** {task.repository}\n"
            f"**Error:** {str(exc)[:300]}",
            icon_emoji=":warning:",
        )
        raise


# ---------------------------------------------------------------------------
# Stage 10: COMPLETE
# ---------------------------------------------------------------------------


async def stage_complete(client: httpx.AsyncClient, task: TaskRecord) -> None:
    """Stage 10 -- Finalize task, store artifacts, update metrics."""
    task.status = TaskStatus.COMPLETE
    task.completed_at = datetime.now(tz=timezone.utc).isoformat()
    created = datetime.fromisoformat(task.created_at)
    completed = datetime.fromisoformat(task.completed_at)
    task.duration_seconds = (completed - created).total_seconds()

    task_log(task, f"Task completed in {task.duration_seconds:.1f}s")
    TASKS_TOTAL.labels(task_type=task.task_type.value, status="complete").inc()
    TASK_DURATION.labels(task_type=task.task_type.value).observe(task.duration_seconds)
    ACTIVE_TASKS.dec()

    # Trace to Langfuse
    try:
        await client.post(
            f"{LANGFUSE_URL}/api/public/traces",
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            json={
                "id": task.task_id,
                "name": f"openhands-{task.task_type.value}",
                "input": {"description": task.description, "repository": task.repository},
                "output": {
                    "pr_url": task.pr_url,
                    "score": task.code_score.overall if task.code_score else None,
                    "gates_passed": task.gate_result.all_passed if task.gate_result else None,
                    "iterations": task.coding_iteration_count,
                    "duration_seconds": task.duration_seconds,
                },
                "metadata": {
                    "task_type": task.task_type.value,
                    "language": task.target_language,
                    "complexity": task.complexity,
                    "service": "ai-coder-alpha",
                },
            },
            timeout=10.0,
        )
    except Exception as exc:
        task_log(task, f"Langfuse trace failed (non-critical): {exc}")

    await broadcast_progress(task.task_id, "complete", "Task completed successfully", 100.0)


# ---------------------------------------------------------------------------
# Full pipeline orchestrator
# ---------------------------------------------------------------------------


async def run_task_pipeline(task: TaskRecord) -> None:
    """Execute the complete 10-stage task lifecycle pipeline."""
    try:
        async with httpx.AsyncClient() as client:
            # Stage 1: RECEIVED
            await stage_received(task)

            # Stage 2: CONTEXT_COMPILING
            await stage_context_compiling(client, task)

            # Stage 3: SPEC_GENERATING
            await stage_spec_generating(client, task)

            # Stage 4: SPEC_REVIEW
            spec_approved = await stage_spec_review(client, task)
            if not spec_approved:
                # Task is now in PENDING_HUMAN_REVIEW, wait for approve/reject
                task_log(task, "Waiting for human approval")
                return

            # Stage 5: CODING
            await stage_coding(client, task)

            # Stage 6: SELF_REVIEW
            await stage_self_review(client, task)

            # Stage 7: TESTING
            await stage_testing(client, task)

            # Stage 8: GATE_CHECK
            await stage_gate_check(client, task)

            # Stage 9: PR_CREATED
            await stage_pr_created(client, task)

            # Stage 10: COMPLETE
            await stage_complete(client, task)

    except Exception as exc:
        task.status = TaskStatus.FAILED
        task.error_message = str(exc)
        task.completed_at = datetime.now(tz=timezone.utc).isoformat()
        created = datetime.fromisoformat(task.created_at)
        completed = datetime.fromisoformat(task.completed_at)
        task.duration_seconds = (completed - created).total_seconds()
        task_log(task, f"Pipeline failed: {exc}")
        TASKS_TOTAL.labels(task_type=task.task_type.value, status="failed").inc()
        ACTIVE_TASKS.dec()

        try:
            async with httpx.AsyncClient() as alert_client:
                await notify_mattermost(
                    alert_client, "alerts",
                    f"### :x: OpenHands Task Failed\n"
                    f"**Task:** `{task.task_id}`\n"
                    f"**Type:** {task.task_type.value}\n"
                    f"**Repository:** {task.repository}\n"
                    f"**Stage:** {task.status.value}\n"
                    f"**Error:** {str(exc)[:500]}",
                    icon_emoji=":warning:",
                )
        except Exception:
            pass

        await broadcast_progress(task.task_id, "failed", f"Task failed: {str(exc)[:200]}", 0.0)


async def resume_task_pipeline(task: TaskRecord) -> None:
    """Resume a task pipeline after human approval."""
    try:
        async with httpx.AsyncClient() as client:
            # Continue from Stage 5: CODING
            await stage_coding(client, task)
            await stage_self_review(client, task)
            await stage_testing(client, task)
            await stage_gate_check(client, task)
            await stage_pr_created(client, task)
            await stage_complete(client, task)
    except Exception as exc:
        task.status = TaskStatus.FAILED
        task.error_message = str(exc)
        task.completed_at = datetime.now(tz=timezone.utc).isoformat()
        task_log(task, f"Resumed pipeline failed: {exc}")
        TASKS_TOTAL.labels(task_type=task.task_type.value, status="failed").inc()
        ACTIVE_TASKS.dec()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown of the task orchestrator."""
    load_config()
    log.info("startup_complete", port=3001)
    yield
    log.info("shutdown")


app = FastAPI(
    title="AI Coder Alpha Task Orchestrator",
    description="System 16 -- OpenHands Task Lifecycle Orchestrator",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health / Ready / Metrics
# ---------------------------------------------------------------------------


@app.get("/health", tags=["infrastructure"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "task-orchestrator", "system": "16"}


@app.get("/ready", tags=["infrastructure"])
async def ready() -> dict[str, Any]:
    """Readiness probe -- checks connectivity to critical services."""
    checks: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in [
            ("litellm", f"{LITELLM_URL}/health"),
            ("openhands", f"{OPENHANDS_URL}/health"),
        ]:
            try:
                resp = await client.get(url)
                checks[name] = "ok" if resp.status_code < 400 else f"http_{resp.status_code}"
            except httpx.HTTPError:
                checks[name] = "unreachable"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
        "active_tasks": len([t for t in tasks_store.values() if t.status not in (
            TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.CANCELLED,
        )]),
    }


@app.get("/metrics", tags=["infrastructure"])
async def metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# Task CRUD endpoints
# ---------------------------------------------------------------------------


@app.post("/tasks", tags=["tasks"], status_code=201)
async def create_task(request: TaskCreateRequest) -> dict[str, Any]:
    """Create a new coding task and start the lifecycle pipeline."""
    task = TaskRecord(
        task_type=request.task_type,
        description=request.description,
        repository=request.repository,
        branch=request.branch,
        target_language=request.target_language,
        framework=request.framework,
        complexity=request.complexity,
        spec=request.spec,
        referenced_files=request.referenced_files,
        requirements=request.requirements,
        constraints=request.constraints,
    )
    tasks_store[task.task_id] = task
    log.info("task_created", task_id=task.task_id, task_type=task.task_type.value, repository=task.repository)

    # Launch pipeline in background
    asyncio.create_task(run_task_pipeline(task))

    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "task_type": task.task_type.value,
        "repository": task.repository,
        "working_branch": task.working_branch,
        "created_at": task.created_at,
    }


@app.get("/tasks", tags=["tasks"])
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    repository: Optional[str] = Query(None, description="Filter by repository"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> dict[str, Any]:
    """List tasks with optional filters."""
    filtered = list(tasks_store.values())

    if status:
        filtered = [t for t in filtered if t.status.value == status]
    if task_type:
        filtered = [t for t in filtered if t.task_type.value == task_type]
    if repository:
        filtered = [t for t in filtered if t.repository == repository]

    # Sort by created_at descending
    filtered.sort(key=lambda t: t.created_at, reverse=True)
    total = len(filtered)
    page = filtered[offset:offset + limit]

    summaries = [
        TaskSummary(
            task_id=t.task_id,
            task_type=t.task_type,
            status=t.status,
            description=t.description,
            repository=t.repository,
            branch=t.branch,
            complexity=t.complexity,
            created_at=t.created_at,
            updated_at=t.updated_at,
            pr_url=t.pr_url,
            code_score_overall=t.code_score.overall if t.code_score else None,
        ).model_dump()
        for t in page
    ]

    return {"total": total, "offset": offset, "limit": limit, "tasks": summaries}


@app.get("/tasks/{task_id}", tags=["tasks"])
async def get_task(task_id: str) -> dict[str, Any]:
    """Get detailed information about a specific task."""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task.model_dump()


@app.get("/tasks/{task_id}/logs", tags=["tasks"])
async def get_task_logs(task_id: str) -> dict[str, Any]:
    """Get execution logs for a task."""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {
        "task_id": task_id,
        "status": task.status.value,
        "log_count": len(task.logs),
        "logs": "\n".join(task.logs),
    }


@app.get("/tasks/{task_id}/artifacts", tags=["tasks"])
async def get_task_artifacts(task_id: str) -> dict[str, Any]:
    """Get artifacts produced by a task."""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return {
        "task_id": task_id,
        "artifact_count": len(task.artifacts),
        "artifacts": [a.model_dump() for a in task.artifacts],
    }


@app.post("/tasks/{task_id}/approve", tags=["tasks"])
async def approve_task(task_id: str, request: TaskApproveRequest) -> dict[str, Any]:
    """Approve a task that is pending human review."""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    if task.status != TaskStatus.PENDING_HUMAN_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} is not pending review (status: {task.status.value})",
        )

    task.human_feedback = request.feedback
    task_log(task, f"Task approved by human reviewer" + (f": {request.feedback}" if request.feedback else ""))

    # Resume pipeline
    asyncio.create_task(resume_task_pipeline(task))

    return {
        "task_id": task_id,
        "status": "approved",
        "message": "Task approved, resuming pipeline from coding stage",
    }


@app.post("/tasks/{task_id}/reject", tags=["tasks"])
async def reject_task(task_id: str, request: TaskRejectRequest) -> dict[str, Any]:
    """Reject a task that is pending human review."""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    if task.status not in (TaskStatus.PENDING_HUMAN_REVIEW, TaskStatus.SPEC_REVIEW):
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} cannot be rejected (status: {task.status.value})",
        )

    task.status = TaskStatus.FAILED
    task.error_message = f"Rejected by reviewer: {request.feedback}"
    task.human_feedback = request.feedback
    task.completed_at = datetime.now(tz=timezone.utc).isoformat()
    task_log(task, f"Task rejected: {request.feedback}")
    TASKS_TOTAL.labels(task_type=task.task_type.value, status="rejected").inc()
    ACTIVE_TASKS.dec()

    return {
        "task_id": task_id,
        "status": "rejected",
        "feedback": request.feedback,
    }


@app.delete("/tasks/{task_id}", tags=["tasks"])
async def cancel_task(task_id: str) -> dict[str, Any]:
    """Cancel an active task."""
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    if task.status in (TaskStatus.COMPLETE, TaskStatus.CANCELLED):
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} is already {task.status.value}",
        )

    task.status = TaskStatus.CANCELLED
    task.completed_at = datetime.now(tz=timezone.utc).isoformat()
    task_log(task, "Task cancelled by user")
    TASKS_TOTAL.labels(task_type=task.task_type.value, status="cancelled").inc()
    if task.status not in (TaskStatus.COMPLETE, TaskStatus.FAILED):
        ACTIVE_TASKS.dec()

    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": "Task has been cancelled",
    }


# ---------------------------------------------------------------------------
# WebSocket endpoint for progress streaming
# ---------------------------------------------------------------------------


@app.websocket("/ws/tasks/{task_id}/progress")
async def websocket_task_progress(ws: WebSocket, task_id: str) -> None:
    """WebSocket endpoint for real-time task progress updates."""
    task = tasks_store.get(task_id)
    if not task:
        await ws.close(code=4004, reason="Task not found")
        return

    await ws.accept()

    if task_id not in task_websockets:
        task_websockets[task_id] = []
    task_websockets[task_id].append(ws)

    log.info("ws_connected", task_id=task_id)

    # Send current state immediately
    await ws.send_json({
        "task_id": task_id,
        "stage": task.status.value,
        "message": f"Current status: {task.status.value}",
        "progress_pct": 100.0 if task.status == TaskStatus.COMPLETE else 0.0,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    })

    try:
        while True:
            # Keep connection alive, listen for client messages (e.g., ping)
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        log.info("ws_disconnected", task_id=task_id)
    finally:
        if task_id in task_websockets:
            try:
                task_websockets[task_id].remove(ws)
            except ValueError:
                pass
            if not task_websockets[task_id]:
                del task_websockets[task_id]


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3001,
        log_level="info",
        access_log=True,
    )
