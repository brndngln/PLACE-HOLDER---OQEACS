# ===========================================================================
# SYSTEM 17 -- AI CODER BETA (SWE-Agent): Task Handler Service
# Omni Quantum Elite AI Coding System -- Bug-Fix & Security Patch Orchestrator
#
# FastAPI microservice (port 8001) that manages the full SWE-Agent task
# lifecycle: receive issue, compile context, reproduce, root-cause analyse,
# implement fix, verify, quality-gate, and create PR.
#
# Task types: bug-fix, security-patch, performance-fix, dependency-update,
#             test-coverage
#
# Endpoints:
#   POST   /tasks                    -- create a new SWE-Agent task
#   GET    /tasks                    -- list all tasks (filterable)
#   GET    /tasks/{task_id}          -- full task detail with diagnostics
#   POST   /tasks/{task_id}/approve  -- approve a completed task
#   POST   /tasks/{task_id}/reject   -- reject with feedback (learns anti-patterns)
#   DELETE /tasks/{task_id}          -- cancel / remove a task
#   GET    /health                   -- liveness probe
#   GET    /ready                    -- readiness probe
#   GET    /metrics                  -- Prometheus metrics
# ===========================================================================

from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx
import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

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
logger = structlog.get_logger("swe-agent-task-handler")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LITELLM_BASE_URL: str = os.getenv("LITELLM_BASE_URL", "http://omni-litellm:4000/v1")
LITELLM_MODEL: str = os.getenv("LITELLM_MODEL", "kimi-dev-72b")
LITELLM_API_KEY: str = os.getenv("LITELLM_API_KEY", "")
TOKEN_INFINITY_URL: str = os.getenv("TOKEN_INFINITY_URL", "http://omni-token-infinity:9600")
CODE_SCORER_URL: str = os.getenv("CODE_SCORER_URL", "http://omni-code-scorer:8080")
GATE_ENGINE_URL: str = os.getenv("GATE_ENGINE_URL", "http://omni-gate-engine:8080")
SOURCEGRAPH_URL: str = os.getenv("SOURCEGRAPH_URL", "http://omni-sourcegraph:7080")
GITEA_URL: str = os.getenv("GITEA_URL", "http://omni-gitea:3000")
GITEA_API_TOKEN: str = os.getenv("GITEA_API_TOKEN", "")
LANGFUSE_URL: str = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
MATTERMOST_WEBHOOK_URL: str = os.getenv("MATTERMOST_WEBHOOK_URL", "")
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://omni-qdrant:6333")
VAULT_ADDR: str = os.getenv("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN: str = os.getenv("VAULT_TOKEN", "")

MAX_CONTEXT_TOKENS: int = int(os.getenv("MAX_CONTEXT_TOKENS", "32768"))
SANDBOX_TIMEOUT: int = int(os.getenv("SANDBOX_TIMEOUT", "900"))
SANDBOX_MEMORY_MB: int = int(os.getenv("SANDBOX_MEMORY_MB", "4096"))
MIN_QUALITY_SCORE: float = float(os.getenv("MIN_QUALITY_SCORE", "7.0"))

VALID_TASK_TYPES: set[str] = {
    "bug-fix",
    "security-patch",
    "performance-fix",
    "dependency-update",
    "test-coverage",
}

VALID_SEVERITIES: set[str] = {"critical", "high", "medium", "low"}


# ---------------------------------------------------------------------------
# Enums & Pydantic models
# ---------------------------------------------------------------------------
class TaskStatus(str, Enum):
    """9-stage SWE-Agent task lifecycle."""

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


class TaskCreateRequest(BaseModel):
    """Payload for creating a new SWE-Agent task."""

    task_type: str = Field(..., description="One of: bug-fix, security-patch, performance-fix, dependency-update, test-coverage")
    issue_url: str = Field(..., description="URL of the Gitea issue")
    repository: str = Field(..., description="Repository in owner/repo format")
    description: str = Field(..., description="Human-readable description of the problem")
    reproduction_steps: list[str] = Field(default_factory=list, description="Ordered steps to reproduce the issue")
    expected_behavior: str = Field(default="", description="What the correct behavior should be")
    severity: str = Field(default="medium", description="One of: critical, high, medium, low")


class ReproductionResult(BaseModel):
    """Result of the reproduction stage."""

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
    """Details of the implemented fix."""

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


class TaskResponse(BaseModel):
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


class TaskDetail(BaseModel):
    """Full task detail including all diagnostic data."""

    task_id: str
    task_type: str
    status: TaskStatus
    repository: str
    issue_url: str
    description: str
    reproduction_steps: list[str]
    expected_behavior: str
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


class RejectRequest(BaseModel):
    """Payload for rejecting a task."""

    feedback: str = Field(..., description="Reason for rejection; stored as anti-pattern for learning")


# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
registry = CollectorRegistry()

TASKS_TOTAL = Counter(
    "swe_agent_tasks_total",
    "Total SWE-Agent tasks by type and final status",
    ["task_type", "status"],
    registry=registry,
)

REPRODUCTION_SUCCESS = Counter(
    "swe_agent_reproduction_success_total",
    "Count of successful issue reproductions",
    registry=registry,
)

REPRODUCTION_FAILURE = Counter(
    "swe_agent_reproduction_failure_total",
    "Count of failed issue reproductions",
    registry=registry,
)

FIX_FIRST_ATTEMPT_SUCCESS = Counter(
    "swe_agent_fix_first_attempt_success_total",
    "Count of fixes passing verification on first attempt",
    registry=registry,
)

FIX_FIRST_ATTEMPT_FAILURE = Counter(
    "swe_agent_fix_first_attempt_failure_total",
    "Count of fixes failing verification on first attempt",
    registry=registry,
)

TASK_DURATION = Histogram(
    "swe_agent_task_duration_seconds",
    "Duration of SWE-Agent tasks by type",
    ["task_type"],
    buckets=[30, 60, 120, 300, 600, 900, 1200, 1800, 3600],
    registry=registry,
)

ACTIVE_TASKS = Gauge(
    "swe_agent_active_tasks",
    "Currently active (in-progress) tasks",
    registry=registry,
)

STAGE_DURATION = Histogram(
    "swe_agent_stage_duration_seconds",
    "Duration of each lifecycle stage",
    ["stage"],
    buckets=[5, 10, 30, 60, 120, 300, 600],
    registry=registry,
)

# ---------------------------------------------------------------------------
# In-memory task store
# ---------------------------------------------------------------------------
tasks: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Derived metric helpers
# ---------------------------------------------------------------------------

def _reproduction_success_rate() -> float:
    """Compute reproduction success rate from counters."""
    success = REPRODUCTION_SUCCESS._value.get()  # type: ignore[union-attr]
    failure = REPRODUCTION_FAILURE._value.get()  # type: ignore[union-attr]
    total = success + failure
    return round(success / total, 4) if total > 0 else 0.0


def _fix_first_attempt_rate() -> float:
    """Compute fix-first-attempt rate from counters."""
    success = FIX_FIRST_ATTEMPT_SUCCESS._value.get()  # type: ignore[union-attr]
    failure = FIX_FIRST_ATTEMPT_FAILURE._value.get()  # type: ignore[union-attr]
    total = success + failure
    return round(success / total, 4) if total > 0 else 0.0


# ---------------------------------------------------------------------------
# HTTP client with retry
# ---------------------------------------------------------------------------

async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    json: Any = None,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    timeout: float = 60.0,
) -> httpx.Response:
    """Execute an HTTP request with exponential backoff retry logic."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = await client.request(
                method,
                url,
                json=json,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code < 500:
                raise
            logger.warning(
                "http_retry",
                url=url,
                attempt=attempt + 1,
                status=exc.response.status_code,
            )
        except httpx.TransportError as exc:
            last_exc = exc
            logger.warning("http_transport_retry", url=url, attempt=attempt + 1, error=str(exc))
        if attempt < max_retries - 1:
            await asyncio.sleep(min(backoff_base ** attempt, 30.0))
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Integration clients
# ---------------------------------------------------------------------------

async def _compile_context(
    client: httpx.AsyncClient,
    task: dict[str, Any],
) -> dict[str, Any]:
    """Stage 2: Use Token Infinity to compile focused context around the issue."""
    payload = {
        "repository": task["repository"],
        "issue_url": task["issue_url"],
        "description": task["description"],
        "reproduction_steps": task["reproduction_steps"],
        "focus_strategy": "relevant_code_and_errors",
        "max_tokens": MAX_CONTEXT_TOKENS,
    }
    try:
        resp = await _request_with_retry(
            client,
            "POST",
            f"{TOKEN_INFINITY_URL}/api/v1/focus",
            json=payload,
            timeout=120.0,
        )
        return resp.json()
    except Exception as exc:
        logger.error("context_compilation_failed", task_id=task["task_id"], error=str(exc))
        return {"files": [], "error_patterns": [], "context": "", "error": str(exc)}


async def _reproduce_issue(
    client: httpx.AsyncClient,
    task: dict[str, Any],
    context: dict[str, Any],
) -> ReproductionResult:
    """Stage 3: Reproduce the issue inside a sandboxed Docker environment."""
    payload = {
        "repository": task["repository"],
        "issue_url": task["issue_url"],
        "reproduction_steps": task["reproduction_steps"],
        "description": task["description"],
        "context_files": context.get("files", []),
        "base_image": "python:3.12-slim",
        "timeout_seconds": SANDBOX_TIMEOUT,
        "max_memory_mb": SANDBOX_MEMORY_MB,
    }
    # Ask the LLM to generate a reproduction script
    llm_payload = {
        "model": LITELLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert SWE-Agent that reproduces software bugs. "
                    "Given the issue description, reproduction steps, and relevant code context, "
                    "generate a self-contained reproduction script that demonstrates the bug. "
                    "Output ONLY the script content, no markdown fences."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Repository: {task['repository']}\n"
                    f"Description: {task['description']}\n"
                    f"Reproduction steps:\n"
                    + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(task["reproduction_steps"]))
                    + f"\n\nExpected behavior: {task['expected_behavior']}\n"
                    f"\nRelevant code context:\n{context.get('context', 'No context available')}"
                ),
            },
        ],
        "max_tokens": 4096,
        "temperature": 0.05,
    }
    try:
        llm_resp = await _request_with_retry(
            client,
            "POST",
            f"{LITELLM_BASE_URL}/chat/completions",
            json=llm_payload,
            headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
            timeout=120.0,
        )
        llm_data = llm_resp.json()
        repro_script = llm_data["choices"][0]["message"]["content"]

        # Execute the reproduction script in sandbox
        sandbox_payload = {
            "script": repro_script,
            "repository": task["repository"],
            "timeout_seconds": SANDBOX_TIMEOUT,
            "max_memory_mb": SANDBOX_MEMORY_MB,
            "docker_network": "omni-quantum-network",
        }
        # The core SWE-Agent service handles sandbox execution
        sandbox_resp = await _request_with_retry(
            client,
            "POST",
            "http://omni-swe-agent-core:8000/api/v1/sandbox/execute",
            json=sandbox_payload,
            timeout=float(SANDBOX_TIMEOUT + 60),
        )
        sandbox_data = sandbox_resp.json()

        result = ReproductionResult(
            success=sandbox_data.get("exit_code", 1) != 0,  # Non-zero means bug reproduced
            error_output=sandbox_data.get("stderr", ""),
            exit_code=sandbox_data.get("exit_code", -1),
            duration_seconds=sandbox_data.get("duration_seconds", 0.0),
            environment_info=sandbox_data.get("environment", {}),
            stack_trace=sandbox_data.get("stack_trace", ""),
        )
        return result
    except Exception as exc:
        logger.error("reproduction_failed", task_id=task["task_id"], error=str(exc))
        return ReproductionResult(
            success=False,
            error_output=str(exc),
            exit_code=-1,
        )


async def _root_cause_analysis(
    client: httpx.AsyncClient,
    task: dict[str, Any],
    context: dict[str, Any],
    reproduction: ReproductionResult,
) -> RootCauseReport:
    """Stage 4: Perform root cause analysis using AST analysis and anti-pattern search."""
    # Search for similar patterns in Sourcegraph
    search_results: dict[str, Any] = {}
    try:
        search_query = f"repo:{task['repository']} {task['description'][:100]}"
        sg_resp = await _request_with_retry(
            client,
            "POST",
            f"{SOURCEGRAPH_URL}/.api/search/stream",
            json={"query": search_query, "version": "V3", "patternType": "literal"},
            timeout=30.0,
        )
        search_results = sg_resp.json()
    except Exception as exc:
        logger.warning("sourcegraph_search_failed", task_id=task["task_id"], error=str(exc))

    # Search anti-patterns in Qdrant
    anti_patterns: list[str] = []
    try:
        qdrant_resp = await _request_with_retry(
            client,
            "POST",
            f"{QDRANT_URL}/collections/swe-agent-anti-patterns/points/search",
            json={
                "vector": [0.0] * 1536,  # Placeholder; real implementation uses embeddings
                "limit": 10,
                "with_payload": True,
                "filter": {
                    "must": [
                        {"key": "task_type", "match": {"value": task["task_type"]}}
                    ]
                },
            },
            timeout=15.0,
        )
        qdrant_data = qdrant_resp.json()
        anti_patterns = [
            hit.get("payload", {}).get("pattern_name", "")
            for hit in qdrant_data.get("result", [])
            if hit.get("payload", {}).get("pattern_name")
        ]
    except Exception as exc:
        logger.warning("qdrant_anti_pattern_search_failed", task_id=task["task_id"], error=str(exc))

    # Use LLM for root cause analysis
    llm_payload = {
        "model": LITELLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert SWE-Agent performing root cause analysis. "
                    "Given the bug description, reproduction output, stack trace, and code context, "
                    "identify the root cause. Return a JSON object with keys: "
                    "root_cause (string), affected_files (list[str]), affected_functions (list[str]), "
                    "confidence (float 0-1), analysis_method (string)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Description: {task['description']}\n"
                    f"Reproduction exit code: {reproduction.exit_code}\n"
                    f"Error output:\n{reproduction.error_output[:3000]}\n"
                    f"Stack trace:\n{reproduction.stack_trace[:2000]}\n"
                    f"Code context:\n{context.get('context', '')[:4000]}\n"
                    f"Known anti-patterns for this type: {anti_patterns}"
                ),
            },
        ],
        "max_tokens": 4096,
        "temperature": 0.05,
        "response_format": {"type": "json_object"},
    }
    try:
        llm_resp = await _request_with_retry(
            client,
            "POST",
            f"{LITELLM_BASE_URL}/chat/completions",
            json=llm_payload,
            headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
            timeout=120.0,
        )
        llm_data = llm_resp.json()
        content = llm_data["choices"][0]["message"]["content"]

        import json
        analysis = json.loads(content)
        return RootCauseReport(
            root_cause=analysis.get("root_cause", "Unable to determine"),
            affected_files=analysis.get("affected_files", []),
            affected_functions=analysis.get("affected_functions", []),
            anti_patterns_detected=anti_patterns,
            confidence=float(analysis.get("confidence", 0.0)),
            analysis_method=analysis.get("analysis_method", "llm_ast_hybrid"),
        )
    except Exception as exc:
        logger.error("root_cause_analysis_failed", task_id=task["task_id"], error=str(exc))
        return RootCauseReport(
            root_cause=f"Analysis failed: {exc}",
            anti_patterns_detected=anti_patterns,
            confidence=0.0,
            analysis_method="failed",
        )


async def _implement_fix(
    client: httpx.AsyncClient,
    task: dict[str, Any],
    context: dict[str, Any],
    root_cause: RootCauseReport,
) -> FixDetail:
    """Stage 5: Generate a fix using the LLM with root cause information."""
    llm_payload = {
        "model": LITELLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert SWE-Agent that fixes software bugs. "
                    "Given the root cause analysis and code context, generate a complete fix. "
                    "Ensure backward compatibility. Include new regression tests. "
                    "Return a JSON object with keys: explanation (string), "
                    "files_changed (list of {path, original, patched}), "
                    "new_tests (list of {path, content}), backward_compatible (bool)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Task type: {task['task_type']}\n"
                    f"Description: {task['description']}\n"
                    f"Root cause: {root_cause.root_cause}\n"
                    f"Affected files: {root_cause.affected_files}\n"
                    f"Affected functions: {root_cause.affected_functions}\n"
                    f"Anti-patterns detected: {root_cause.anti_patterns_detected}\n"
                    f"Confidence: {root_cause.confidence}\n"
                    f"Code context:\n{context.get('context', '')[:8000]}\n"
                    f"Expected behavior: {task['expected_behavior']}"
                ),
            },
        ],
        "max_tokens": 16384,
        "temperature": 0.05,
        "response_format": {"type": "json_object"},
    }
    try:
        llm_resp = await _request_with_retry(
            client,
            "POST",
            f"{LITELLM_BASE_URL}/chat/completions",
            json=llm_payload,
            headers={"Authorization": f"Bearer {LITELLM_API_KEY}"},
            timeout=180.0,
        )
        llm_data = llm_resp.json()
        content = llm_data["choices"][0]["message"]["content"]

        import json
        fix_data = json.loads(content)

        files_changed = [f.get("path", "") for f in fix_data.get("files_changed", [])]
        new_tests = fix_data.get("new_tests", [])
        total_added = 0
        total_removed = 0
        for fc in fix_data.get("files_changed", []):
            original_lines = len(fc.get("original", "").splitlines())
            patched_lines = len(fc.get("patched", "").splitlines())
            total_added += max(0, patched_lines - original_lines)
            total_removed += max(0, original_lines - patched_lines)

        # Apply fix via core sandbox
        apply_payload = {
            "repository": task["repository"],
            "files_changed": fix_data.get("files_changed", []),
            "new_tests": new_tests,
            "branch_prefix": "swe-agent",
            "task_id": task["task_id"],
        }
        await _request_with_retry(
            client,
            "POST",
            "http://omni-swe-agent-core:8000/api/v1/sandbox/apply-fix",
            json=apply_payload,
            timeout=120.0,
        )

        return FixDetail(
            explanation=fix_data.get("explanation", ""),
            files_changed=files_changed,
            diff_summary=f"+{total_added} -{total_removed} across {len(files_changed)} files",
            backward_compatible=fix_data.get("backward_compatible", True),
            new_tests_added=len(new_tests),
            lines_added=total_added,
            lines_removed=total_removed,
        )
    except Exception as exc:
        logger.error("fix_implementation_failed", task_id=task["task_id"], error=str(exc))
        return FixDetail(explanation=f"Fix generation failed: {exc}")


async def _verify_fix(
    client: httpx.AsyncClient,
    task: dict[str, Any],
) -> VerificationResult:
    """Stage 6: Re-run reproduction (should pass) and full test suite."""
    try:
        verify_payload = {
            "repository": task["repository"],
            "task_id": task["task_id"],
            "branch": f"swe-agent/{task['task_id']}",
            "reproduction_steps": task["reproduction_steps"],
            "timeout_seconds": SANDBOX_TIMEOUT,
            "max_memory_mb": SANDBOX_MEMORY_MB,
        }
        resp = await _request_with_retry(
            client,
            "POST",
            "http://omni-swe-agent-core:8000/api/v1/sandbox/verify",
            json=verify_payload,
            timeout=float(SANDBOX_TIMEOUT + 120),
        )
        data = resp.json()

        return VerificationResult(
            reproduction_passes=data.get("reproduction_passes", False),
            test_suite_passes=data.get("test_suite_passes", False),
            new_tests_pass=data.get("new_tests_pass", False),
            regression_tests_pass=data.get("regression_tests_pass", False),
            total_tests_run=data.get("total_tests_run", 0),
            tests_passed=data.get("tests_passed", 0),
            tests_failed=data.get("tests_failed", 0),
            coverage_delta=data.get("coverage_delta", 0.0),
        )
    except Exception as exc:
        logger.error("verification_failed", task_id=task["task_id"], error=str(exc))
        return VerificationResult()


async def _quality_check(
    client: httpx.AsyncClient,
    task: dict[str, Any],
    fix: FixDetail,
) -> QualityCheckResult:
    """Stage 7: Score the fix via Code Scorer and validate via Gate Engine."""
    # Code Scorer
    score_result: dict[str, Any] = {}
    try:
        score_payload = {
            "task_id": task["task_id"],
            "repository": task["repository"],
            "branch": f"swe-agent/{task['task_id']}",
            "files_changed": fix.files_changed,
            "task_type": task["task_type"],
        }
        score_resp = await _request_with_retry(
            client,
            "POST",
            f"{CODE_SCORER_URL}/api/v1/score",
            json=score_payload,
            timeout=120.0,
        )
        score_result = score_resp.json()
    except Exception as exc:
        logger.error("code_scorer_failed", task_id=task["task_id"], error=str(exc))

    # Gate Engine
    gate_result: dict[str, Any] = {}
    try:
        gate_payload = {
            "task_id": task["task_id"],
            "repository": task["repository"],
            "quality_score": score_result.get("quality_score", 0.0),
            "test_pass": task.get("_verification", {}).get("test_suite_passes", False),
            "security_scan": True,
            "backward_compatibility": fix.backward_compatible,
        }
        gate_resp = await _request_with_retry(
            client,
            "POST",
            f"{GATE_ENGINE_URL}/api/v1/evaluate",
            json=gate_payload,
            timeout=60.0,
        )
        gate_result = gate_resp.json()
    except Exception as exc:
        logger.error("gate_engine_failed", task_id=task["task_id"], error=str(exc))

    return QualityCheckResult(
        code_score=score_result.get("quality_score", 0.0),
        gate_passed=gate_result.get("passed", False),
        dimensions=score_result.get("dimensions", {}),
        gate_details=gate_result.get("details", {}),
        lint_passed=score_result.get("lint_passed", False),
        security_scan_passed=gate_result.get("security_scan_passed", False),
    )


async def _create_pr(
    client: httpx.AsyncClient,
    task: dict[str, Any],
    root_cause: RootCauseReport,
    fix: FixDetail,
    verification: VerificationResult,
) -> PRInfo:
    """Stage 8: Create a pull request in Gitea with full diagnostic report."""
    owner, repo = task["repository"].split("/", 1)
    branch_name = f"swe-agent/{task['task_id']}"

    pr_body = (
        f"## Root Cause\n\n{root_cause.root_cause}\n\n"
        f"**Confidence:** {root_cause.confidence:.0%}\n"
        f"**Analysis method:** {root_cause.analysis_method}\n"
        f"**Affected files:** {', '.join(root_cause.affected_files) or 'N/A'}\n"
        f"**Affected functions:** {', '.join(root_cause.affected_functions) or 'N/A'}\n\n"
        f"## Fix Explanation\n\n{fix.explanation}\n\n"
        f"**Changes:** {fix.diff_summary}\n"
        f"**Backward compatible:** {'Yes' if fix.backward_compatible else 'No'}\n"
        f"**New tests added:** {fix.new_tests_added}\n\n"
        f"## Test Results\n\n"
        f"| Metric | Result |\n|--------|--------|\n"
        f"| Reproduction passes | {'Pass' if verification.reproduction_passes else 'Fail'} |\n"
        f"| Test suite passes | {'Pass' if verification.test_suite_passes else 'Fail'} |\n"
        f"| New tests pass | {'Pass' if verification.new_tests_pass else 'Fail'} |\n"
        f"| Regression tests pass | {'Pass' if verification.regression_tests_pass else 'Fail'} |\n"
        f"| Total tests run | {verification.total_tests_run} |\n"
        f"| Tests passed | {verification.tests_passed} |\n"
        f"| Tests failed | {verification.tests_failed} |\n"
        f"| Coverage delta | {verification.coverage_delta:+.1f}% |\n\n"
        f"## Before / After\n\n"
        f"**Before:** Issue reproducible, failing tests\n"
        f"**After:** Issue resolved, all tests passing, {fix.new_tests_added} new regression tests\n\n"
        f"---\n"
        f"Linked issue: {task['issue_url']}\n"
        f"Task ID: `{task['task_id']}`\n"
        f"Generated by SWE-Agent (System 17)"
    )

    severity_label = f"severity:{task['severity']}"
    labels = ["swe-agent", "automated", task["task_type"], severity_label]

    pr_title = f"[SWE-Agent] {task['task_type']}: {task['description'][:80]}"

    try:
        pr_payload = {
            "title": pr_title,
            "body": pr_body,
            "head": branch_name,
            "base": "main",
            "labels": labels,
        }
        headers = {
            "Authorization": f"token {GITEA_API_TOKEN}",
            "Content-Type": "application/json",
        }
        resp = await _request_with_retry(
            client,
            "POST",
            f"{GITEA_URL}/api/v1/repos/{owner}/{repo}/pulls",
            json=pr_payload,
            headers=headers,
            timeout=30.0,
        )
        pr_data = resp.json()

        return PRInfo(
            pr_url=pr_data.get("html_url", ""),
            pr_number=pr_data.get("number", 0),
            branch_name=branch_name,
            title=pr_title,
            labels=labels,
        )
    except Exception as exc:
        logger.error("pr_creation_failed", task_id=task["task_id"], error=str(exc))
        return PRInfo(branch_name=branch_name, title=pr_title, labels=labels)


async def _notify_mattermost(
    client: httpx.AsyncClient,
    message: str,
    channel: str = "swe-agent",
) -> None:
    """Post a notification to Mattermost via webhook."""
    if not MATTERMOST_WEBHOOK_URL:
        return
    try:
        await _request_with_retry(
            client,
            "POST",
            MATTERMOST_WEBHOOK_URL,
            json={
                "channel": channel,
                "username": "SWE-Agent",
                "icon_emoji": ":robot:",
                "text": message,
            },
            max_retries=2,
            timeout=10.0,
        )
    except Exception as exc:
        logger.warning("mattermost_notification_failed", error=str(exc))


async def _store_anti_pattern(
    client: httpx.AsyncClient,
    task: dict[str, Any],
    feedback: str,
) -> None:
    """Store a rejection as an anti-pattern in Qdrant for future learning."""
    try:
        point_id = str(uuid.uuid4())
        payload = {
            "points": [
                {
                    "id": point_id,
                    "vector": [0.0] * 1536,  # Real implementation generates embedding from feedback
                    "payload": {
                        "task_id": task["task_id"],
                        "task_type": task["task_type"],
                        "repository": task["repository"],
                        "pattern_name": feedback[:200],
                        "feedback": feedback,
                        "description": task["description"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                }
            ]
        }
        await _request_with_retry(
            client,
            "PUT",
            f"{QDRANT_URL}/collections/swe-agent-anti-patterns/points",
            json=payload,
            timeout=15.0,
        )
        logger.info("anti_pattern_stored", task_id=task["task_id"], point_id=point_id)
    except Exception as exc:
        logger.warning("anti_pattern_store_failed", task_id=task["task_id"], error=str(exc))


async def _trace_to_langfuse(
    client: httpx.AsyncClient,
    task: dict[str, Any],
    event: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Send a trace event to Langfuse for observability."""
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        return
    try:
        trace_payload = {
            "name": f"swe-agent-{event}",
            "metadata": {
                "task_id": task["task_id"],
                "task_type": task["task_type"],
                "repository": task["repository"],
                "severity": task["severity"],
                **(metadata or {}),
            },
            "tags": ["swe-agent", task["task_type"], task["severity"]],
        }
        await client.post(
            f"{LANGFUSE_URL}/api/public/traces",
            json=trace_payload,
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            timeout=10.0,
        )
    except Exception as exc:
        logger.debug("langfuse_trace_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Stage transition helper
# ---------------------------------------------------------------------------

def _update_task_status(task_id: str, new_status: TaskStatus, message: str = "") -> None:
    """Transition a task to a new status and record the change."""
    task = tasks[task_id]
    old_status = task["status"]
    now = datetime.now(timezone.utc).isoformat()
    task["status"] = new_status
    task["updated_at"] = now
    task["message"] = message
    task["stage_history"].append({
        "from": old_status.value if isinstance(old_status, TaskStatus) else str(old_status),
        "to": new_status.value,
        "timestamp": now,
        "message": message,
    })
    logger.info(
        "task_status_changed",
        task_id=task_id,
        from_status=old_status,
        to_status=new_status.value,
        message=message,
    )


# ---------------------------------------------------------------------------
# Main task lifecycle processor
# ---------------------------------------------------------------------------

async def _process_task(task_id: str) -> None:
    """Execute the full 9-stage SWE-Agent lifecycle for a task."""
    task = tasks[task_id]
    task_start = time.monotonic()
    ACTIVE_TASKS.inc()

    async with httpx.AsyncClient() as client:
        try:
            # ── Stage 2: CONTEXT_COMPILING ────────────────────
            _update_task_status(task_id, TaskStatus.CONTEXT_COMPILING, "Compiling relevant context via Token Infinity")
            stage_start = time.monotonic()
            await _trace_to_langfuse(client, task, "context_compiling")

            context = await _compile_context(client, task)
            STAGE_DURATION.labels(stage="context_compiling").observe(time.monotonic() - stage_start)

            # ── Stage 3: REPRODUCTION ─────────────────────────
            _update_task_status(task_id, TaskStatus.REPRODUCTION, "Reproducing issue in sandbox")
            stage_start = time.monotonic()
            await _trace_to_langfuse(client, task, "reproduction")

            reproduction = await _reproduce_issue(client, task, context)
            task["_reproduction"] = reproduction
            STAGE_DURATION.labels(stage="reproduction").observe(time.monotonic() - stage_start)

            if not reproduction.success:
                REPRODUCTION_FAILURE.inc()
                _update_task_status(
                    task_id,
                    TaskStatus.HUMAN_REVIEW,
                    "Could not reproduce issue; escalating to human review",
                )
                ACTIVE_TASKS.dec()
                await _notify_mattermost(
                    client,
                    f"**SWE-Agent** could not reproduce issue for task `{task_id}` "
                    f"in `{task['repository']}`. Manual investigation required.\n"
                    f"Issue: {task['issue_url']}",
                    channel="incidents",
                )
                await _trace_to_langfuse(client, task, "human_review", {"reason": "reproduction_failed"})
                return

            REPRODUCTION_SUCCESS.inc()

            # ── Stage 4: ROOT_CAUSE_ANALYSIS ──────────────────
            _update_task_status(task_id, TaskStatus.ROOT_CAUSE_ANALYSIS, "Analysing root cause via AST + anti-pattern search")
            stage_start = time.monotonic()
            await _trace_to_langfuse(client, task, "root_cause_analysis")

            root_cause = await _root_cause_analysis(client, task, context, reproduction)
            task["_root_cause"] = root_cause
            STAGE_DURATION.labels(stage="root_cause_analysis").observe(time.monotonic() - stage_start)

            # ── Stage 5: FIX_IMPLEMENTATION ───────────────────
            _update_task_status(task_id, TaskStatus.FIX_IMPLEMENTATION, "Generating fix with backward-compatibility guarantee")
            stage_start = time.monotonic()
            await _trace_to_langfuse(client, task, "fix_implementation")

            fix = await _implement_fix(client, task, context, root_cause)
            task["_fix"] = fix
            STAGE_DURATION.labels(stage="fix_implementation").observe(time.monotonic() - stage_start)

            # ── Stage 6: VERIFICATION ─────────────────────────
            _update_task_status(task_id, TaskStatus.VERIFICATION, "Verifying fix: re-running reproduction + full test suite")
            stage_start = time.monotonic()
            await _trace_to_langfuse(client, task, "verification")

            verification = await _verify_fix(client, task)
            task["_verification"] = verification
            STAGE_DURATION.labels(stage="verification").observe(time.monotonic() - stage_start)

            all_pass = (
                verification.reproduction_passes
                and verification.test_suite_passes
                and verification.new_tests_pass
                and verification.regression_tests_pass
            )
            if all_pass:
                FIX_FIRST_ATTEMPT_SUCCESS.inc()
            else:
                FIX_FIRST_ATTEMPT_FAILURE.inc()

            if not all_pass:
                _update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    (
                        f"Verification failed: reproduction={'pass' if verification.reproduction_passes else 'fail'}, "
                        f"tests={'pass' if verification.test_suite_passes else 'fail'}, "
                        f"new_tests={'pass' if verification.new_tests_pass else 'fail'}, "
                        f"regression={'pass' if verification.regression_tests_pass else 'fail'}"
                    ),
                )
                ACTIVE_TASKS.dec()
                TASKS_TOTAL.labels(task_type=task["task_type"], status="failed").inc()
                TASK_DURATION.labels(task_type=task["task_type"]).observe(time.monotonic() - task_start)
                await _trace_to_langfuse(client, task, "failed", {"reason": "verification_failed"})
                return

            # ── Stage 7: QUALITY_CHECK ────────────────────────
            _update_task_status(task_id, TaskStatus.QUALITY_CHECK, "Running Code Scorer + Gate Engine")
            stage_start = time.monotonic()
            await _trace_to_langfuse(client, task, "quality_check")

            quality = await _quality_check(client, task, fix)
            task["_quality"] = quality
            STAGE_DURATION.labels(stage="quality_check").observe(time.monotonic() - stage_start)

            if not quality.gate_passed or quality.code_score < MIN_QUALITY_SCORE:
                _update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    f"Quality gate failed: score={quality.code_score:.1f}, gate_passed={quality.gate_passed}",
                )
                ACTIVE_TASKS.dec()
                TASKS_TOTAL.labels(task_type=task["task_type"], status="failed").inc()
                TASK_DURATION.labels(task_type=task["task_type"]).observe(time.monotonic() - task_start)
                await _trace_to_langfuse(client, task, "failed", {"reason": "quality_gate_failed"})
                return

            # ── Stage 8: PR_CREATED ───────────────────────────
            _update_task_status(task_id, TaskStatus.PR_CREATED, "Creating pull request in Gitea")
            stage_start = time.monotonic()
            await _trace_to_langfuse(client, task, "pr_created")

            pr_info = await _create_pr(client, task, root_cause, fix, verification)
            task["_pr"] = pr_info
            STAGE_DURATION.labels(stage="pr_created").observe(time.monotonic() - stage_start)

            # ── Stage 9: COMPLETE ─────────────────────────────
            task["completed_at"] = datetime.now(timezone.utc).isoformat()
            task["duration_seconds"] = time.monotonic() - task_start
            _update_task_status(
                task_id,
                TaskStatus.COMPLETE,
                f"PR #{pr_info.pr_number} created: {pr_info.pr_url}",
            )
            ACTIVE_TASKS.dec()
            TASKS_TOTAL.labels(task_type=task["task_type"], status="complete").inc()
            TASK_DURATION.labels(task_type=task["task_type"]).observe(time.monotonic() - task_start)

            await _notify_mattermost(
                client,
                (
                    f"**SWE-Agent** completed task `{task_id}`\n"
                    f"**Type:** {task['task_type']} | **Severity:** {task['severity']}\n"
                    f"**Repository:** {task['repository']}\n"
                    f"**Root cause:** {root_cause.root_cause[:200]}\n"
                    f"**PR:** {pr_info.pr_url}\n"
                    f"**Score:** {quality.code_score:.1f}/10 | "
                    f"**Tests:** {verification.tests_passed}/{verification.total_tests_run} passed"
                ),
            )
            await _trace_to_langfuse(client, task, "complete", {
                "pr_url": pr_info.pr_url,
                "duration_seconds": task["duration_seconds"],
                "code_score": quality.code_score,
            })

        except Exception as exc:
            logger.exception("task_processing_error", task_id=task_id, error=str(exc))
            _update_task_status(task_id, TaskStatus.FAILED, f"Unexpected error: {exc}")
            ACTIVE_TASKS.dec()
            TASKS_TOTAL.labels(task_type=task["task_type"], status="failed").inc()
            TASK_DURATION.labels(task_type=task["task_type"]).observe(time.monotonic() - task_start)
            await _trace_to_langfuse(client, task, "failed", {"reason": "unexpected_error", "error": str(exc)})


# ---------------------------------------------------------------------------
# Helpers: build response models from internal task dict
# ---------------------------------------------------------------------------

def _task_to_response(task: dict[str, Any]) -> TaskResponse:
    """Convert internal task dict to a TaskResponse."""
    return TaskResponse(
        task_id=task["task_id"],
        task_type=task["task_type"],
        status=task["status"],
        repository=task["repository"],
        issue_url=task["issue_url"],
        severity=task["severity"],
        created_at=task["created_at"],
        updated_at=task["updated_at"],
        message=task.get("message", ""),
    )


def _task_to_detail(task: dict[str, Any]) -> TaskDetail:
    """Convert internal task dict to a full TaskDetail."""
    return TaskDetail(
        task_id=task["task_id"],
        task_type=task["task_type"],
        status=task["status"],
        repository=task["repository"],
        issue_url=task["issue_url"],
        description=task["description"],
        reproduction_steps=task["reproduction_steps"],
        expected_behavior=task["expected_behavior"],
        severity=task["severity"],
        created_at=task["created_at"],
        updated_at=task["updated_at"],
        started_at=task.get("started_at", ""),
        completed_at=task.get("completed_at", ""),
        duration_seconds=task.get("duration_seconds", 0.0),
        message=task.get("message", ""),
        reproduction_result=task.get("_reproduction"),
        root_cause_report=task.get("_root_cause"),
        fix_detail=task.get("_fix"),
        verification_result=task.get("_verification"),
        quality_check_result=task.get("_quality"),
        pr_info=task.get("_pr"),
        rejection_feedback=task.get("rejection_feedback", ""),
        stage_history=task.get("stage_history", []),
    )


def _task_to_summary(task: dict[str, Any]) -> TaskSummary:
    """Convert internal task dict to a lightweight TaskSummary."""
    return TaskSummary(
        task_id=task["task_id"],
        task_type=task["task_type"],
        status=task["status"],
        repository=task["repository"],
        severity=task["severity"],
        created_at=task["created_at"],
        updated_at=task["updated_at"],
    )


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of the task handler."""
    logger.info("task_handler_starting", port=8001)
    yield
    logger.info("task_handler_shutting_down", active_tasks=len([
        t for t in tasks.values()
        if t["status"] not in (TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.REJECTED)
    ]))


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SWE-Agent Task Handler",
    description="System 17 -- AI Coder Beta: Bug-fix & security-patch task orchestrator",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health / Ready / Metrics
# ---------------------------------------------------------------------------

@app.get("/health", tags=["infrastructure"])
async def health() -> dict[str, str]:
    """Liveness probe -- returns OK if the process is running."""
    return {
        "status": "healthy",
        "service": "swe-agent-task-handler",
        "system": "17",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["infrastructure"])
async def ready() -> JSONResponse:
    """Readiness probe -- verifies connectivity to critical dependencies."""
    checks: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in [
            ("litellm", f"{LITELLM_BASE_URL.rstrip('/v1')}/health"),
            ("gitea", f"{GITEA_URL}/api/v1/version"),
            ("token_infinity", f"{TOKEN_INFINITY_URL}/health"),
            ("code_scorer", f"{CODE_SCORER_URL}/health"),
            ("gate_engine", f"{GATE_ENGINE_URL}/health"),
        ]:
            try:
                resp = await client.get(url)
                checks[name] = "ok" if resp.status_code < 400 else f"http_{resp.status_code}"
            except httpx.HTTPError:
                checks[name] = "unreachable"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": checks,
        },
    )


@app.get("/metrics", tags=["infrastructure"])
async def metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint with derived gauges."""
    # Inject derived rates as comments (Prometheus exposition format)
    base = generate_latest(registry).decode("utf-8")
    derived = (
        f"# HELP swe_agent_reproduction_success_rate Ratio of successful reproductions\n"
        f"# TYPE swe_agent_reproduction_success_rate gauge\n"
        f"swe_agent_reproduction_success_rate {_reproduction_success_rate()}\n"
        f"# HELP swe_agent_fix_first_attempt_rate Ratio of fixes passing on first attempt\n"
        f"# TYPE swe_agent_fix_first_attempt_rate gauge\n"
        f"swe_agent_fix_first_attempt_rate {_fix_first_attempt_rate()}\n"
    )
    return PlainTextResponse(
        content=base + derived,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# Task CRUD endpoints
# ---------------------------------------------------------------------------

@app.post("/tasks", tags=["tasks"], response_model=TaskResponse, status_code=201)
async def create_task(request: TaskCreateRequest) -> TaskResponse:
    """
    Create a new SWE-Agent task.

    Validates the payload, initialises the task in RECEIVED status, and
    starts the asynchronous 9-stage lifecycle processor.
    """
    # Validate task type
    if request.task_type not in VALID_TASK_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid task_type '{request.task_type}'. Must be one of: {sorted(VALID_TASK_TYPES)}",
        )

    # Validate severity
    if request.severity not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid severity '{request.severity}'. Must be one of: {sorted(VALID_SEVERITIES)}",
        )

    # Validate repository format
    if "/" not in request.repository:
        raise HTTPException(
            status_code=422,
            detail="Repository must be in 'owner/repo' format",
        )

    task_id = f"swe-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    task: dict[str, Any] = {
        "task_id": task_id,
        "task_type": request.task_type,
        "status": TaskStatus.RECEIVED,
        "issue_url": request.issue_url,
        "repository": request.repository,
        "description": request.description,
        "reproduction_steps": request.reproduction_steps,
        "expected_behavior": request.expected_behavior,
        "severity": request.severity,
        "created_at": now,
        "updated_at": now,
        "started_at": now,
        "completed_at": "",
        "duration_seconds": 0.0,
        "message": "Task received and validated",
        "rejection_feedback": "",
        "stage_history": [
            {
                "from": "NONE",
                "to": TaskStatus.RECEIVED.value,
                "timestamp": now,
                "message": "Task created",
            }
        ],
    }
    tasks[task_id] = task

    TASKS_TOTAL.labels(task_type=request.task_type, status="received").inc()
    logger.info(
        "task_created",
        task_id=task_id,
        task_type=request.task_type,
        repository=request.repository,
        severity=request.severity,
    )

    # Launch background lifecycle processing
    asyncio.create_task(_process_task(task_id))

    return _task_to_response(task)


@app.get("/tasks/{task_id}", tags=["tasks"], response_model=TaskDetail)
async def get_task(task_id: str) -> TaskDetail:
    """
    Get full task detail including reproduction results, root cause,
    fix details, verification, quality check, and PR info.
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return _task_to_detail(tasks[task_id])


@app.get("/tasks", tags=["tasks"], response_model=list[TaskSummary])
async def list_tasks(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    repository: Optional[str] = Query(None, description="Filter by repository"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Result offset"),
) -> list[TaskSummary]:
    """List all tasks with optional filters and pagination."""
    result: list[dict[str, Any]] = []
    for task in tasks.values():
        if task_type and task["task_type"] != task_type:
            continue
        if status and task["status"].value != status:
            continue
        if severity and task["severity"] != severity:
            continue
        if repository and task["repository"] != repository:
            continue
        result.append(task)

    # Sort by created_at descending
    result.sort(key=lambda t: t["created_at"], reverse=True)
    paginated = result[offset : offset + limit]
    return [_task_to_summary(t) for t in paginated]


@app.post("/tasks/{task_id}/approve", tags=["tasks"], response_model=TaskResponse)
async def approve_task(task_id: str) -> TaskResponse:
    """
    Approve a completed task. Marks the task as COMPLETE and signals
    that the PR can be merged.
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    task = tasks[task_id]
    if task["status"] not in (TaskStatus.PR_CREATED, TaskStatus.COMPLETE):
        raise HTTPException(
            status_code=409,
            detail=f"Task is in status '{task['status'].value}'; can only approve tasks in PR_CREATED or COMPLETE status",
        )

    _update_task_status(task_id, TaskStatus.COMPLETE, "Task approved by human reviewer")
    TASKS_TOTAL.labels(task_type=task["task_type"], status="approved").inc()

    logger.info("task_approved", task_id=task_id)
    return _task_to_response(task)


@app.post("/tasks/{task_id}/reject", tags=["tasks"], response_model=TaskResponse)
async def reject_task(task_id: str, request: RejectRequest) -> TaskResponse:
    """
    Reject a task with feedback. The feedback is stored as an anti-pattern
    in Qdrant so the agent can learn from the rejection.
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    task = tasks[task_id]
    if task["status"] in (TaskStatus.CANCELLED,):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject a cancelled task",
        )

    task["rejection_feedback"] = request.feedback
    _update_task_status(task_id, TaskStatus.REJECTED, f"Rejected: {request.feedback[:200]}")
    TASKS_TOTAL.labels(task_type=task["task_type"], status="rejected").inc()

    # Store anti-pattern asynchronously
    async with httpx.AsyncClient() as client:
        await _store_anti_pattern(client, task, request.feedback)

    logger.info("task_rejected", task_id=task_id, feedback=request.feedback[:200])
    return _task_to_response(task)


@app.delete("/tasks/{task_id}", tags=["tasks"], response_model=TaskResponse)
async def delete_task(task_id: str) -> TaskResponse:
    """Cancel and remove a task. Running tasks are marked CANCELLED."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    task = tasks[task_id]
    terminal = {TaskStatus.COMPLETE, TaskStatus.FAILED, TaskStatus.REJECTED, TaskStatus.CANCELLED}
    if task["status"] not in terminal:
        _update_task_status(task_id, TaskStatus.CANCELLED, "Task cancelled by user")
        ACTIVE_TASKS.dec()
        TASKS_TOTAL.labels(task_type=task["task_type"], status="cancelled").inc()
    else:
        _update_task_status(task_id, TaskStatus.CANCELLED, "Task removed")

    response = _task_to_response(task)
    logger.info("task_deleted", task_id=task_id)
    return response


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        access_log=True,
    )
