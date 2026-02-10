# ===========================================================================
# SYSTEM 17 -- AI CODER BETA (SWE-Agent): Issue Intake Service
# Omni Quantum Elite AI Coding System -- Gitea Issue Webhook Processor
#
# FastAPI microservice (port 8002) that receives Gitea issue webhooks,
# filters for issues labelled "swe-agent", parses the issue body for
# reproduction steps and severity, creates a task via the Task Handler,
# and posts an acknowledgement comment on the Gitea issue.
#
# Endpoints:
#   POST /webhook/gitea/issue  -- Gitea issue webhook receiver
#   GET  /health               -- liveness probe
#   GET  /metrics              -- Prometheus metrics
# ===========================================================================

from __future__ import annotations

import hashlib
import hmac
import os
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from prometheus_client import (
    CollectorRegistry,
    Counter,
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
logger = structlog.get_logger("swe-agent-issue-intake")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TASK_HANDLER_URL: str = os.getenv("TASK_HANDLER_URL", "http://omni-swe-agent-task-handler:8001")
GITEA_URL: str = os.getenv("GITEA_URL", "http://omni-gitea:3000")
GITEA_API_TOKEN: str = os.getenv("GITEA_API_TOKEN", "")
GITEA_WEBHOOK_SECRET: str = os.getenv("GITEA_WEBHOOK_SECRET", "")
VAULT_ADDR: str = os.getenv("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN: str = os.getenv("VAULT_TOKEN", "")

SWE_AGENT_LABEL: str = "swe-agent"
MAX_RETRY_ATTEMPTS: int = 3
RETRY_BACKOFF_BASE: float = 2.0

# ---------------------------------------------------------------------------
# Severity mapping from issue labels
# ---------------------------------------------------------------------------
SEVERITY_LABEL_MAP: dict[str, str] = {
    "critical": "critical",
    "severity:critical": "critical",
    "p0": "critical",
    "high": "high",
    "severity:high": "high",
    "p1": "high",
    "medium": "medium",
    "severity:medium": "medium",
    "p2": "medium",
    "low": "low",
    "severity:low": "low",
    "p3": "low",
}

# Task type mapping from issue labels
TASK_TYPE_LABEL_MAP: dict[str, str] = {
    "bug": "bug-fix",
    "bug-fix": "bug-fix",
    "security": "security-patch",
    "security-patch": "security-patch",
    "vulnerability": "security-patch",
    "cve": "security-patch",
    "performance": "performance-fix",
    "performance-fix": "performance-fix",
    "slow": "performance-fix",
    "dependency": "dependency-update",
    "dependency-update": "dependency-update",
    "deps": "dependency-update",
    "test": "test-coverage",
    "test-coverage": "test-coverage",
    "coverage": "test-coverage",
}

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
registry = CollectorRegistry()

WEBHOOKS_RECEIVED = Counter(
    "swe_agent_intake_webhooks_received_total",
    "Total Gitea webhooks received",
    registry=registry,
)

WEBHOOKS_PROCESSED = Counter(
    "swe_agent_intake_webhooks_processed_total",
    "Webhooks that matched swe-agent label and were processed",
    registry=registry,
)

WEBHOOKS_SKIPPED = Counter(
    "swe_agent_intake_webhooks_skipped_total",
    "Webhooks skipped (no swe-agent label or wrong action)",
    ["reason"],
    registry=registry,
)

WEBHOOKS_ERRORS = Counter(
    "swe_agent_intake_errors_total",
    "Errors during webhook processing",
    ["stage"],
    registry=registry,
)

TASKS_CREATED = Counter(
    "swe_agent_intake_tasks_created_total",
    "Tasks successfully created via task handler",
    ["task_type"],
    registry=registry,
)

WEBHOOK_LATENCY = Histogram(
    "swe_agent_intake_webhook_duration_seconds",
    "Webhook processing latency",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
    registry=registry,
)


# ---------------------------------------------------------------------------
# Pydantic models for webhook payload
# ---------------------------------------------------------------------------

class GiteaLabel(BaseModel):
    """Gitea issue label."""

    id: int = 0
    name: str = ""
    color: str = ""


class GiteaUser(BaseModel):
    """Gitea user reference."""

    id: int = 0
    login: str = ""
    full_name: str = ""


class GiteaRepository(BaseModel):
    """Gitea repository reference."""

    id: int = 0
    name: str = ""
    full_name: str = ""
    html_url: str = ""
    clone_url: str = ""


class GiteaIssue(BaseModel):
    """Gitea issue object from webhook."""

    id: int = 0
    number: int = 0
    title: str = ""
    body: str = ""
    html_url: str = ""
    state: str = ""
    labels: list[GiteaLabel] = Field(default_factory=list)
    user: Optional[GiteaUser] = None


class GiteaIssueWebhook(BaseModel):
    """Top-level Gitea issue webhook payload."""

    action: str = ""
    issue: Optional[GiteaIssue] = None
    repository: Optional[GiteaRepository] = None
    sender: Optional[GiteaUser] = None


# ---------------------------------------------------------------------------
# Issue body parser
# ---------------------------------------------------------------------------

def _extract_reproduction_steps(body: str) -> list[str]:
    """
    Parse reproduction steps from an issue body.

    Supports multiple formats:
    - Numbered lists: 1. step one, 2. step two
    - Bullet lists under a 'reproduction' or 'steps to reproduce' heading
    - Lines starting with '- ' under relevant headings
    """
    steps: list[str] = []

    # Try to find a section headed "Steps to Reproduce" / "Reproduction" / "How to reproduce"
    section_pattern = re.compile(
        r"(?:#{1,4}\s*)?(?:steps?\s+to\s+reproduce|reproduction\s+steps?|how\s+to\s+reproduce|reproduce)\s*:?\s*\n([\s\S]*?)(?=\n#{1,4}\s|\n\n\n|\Z)",
        re.IGNORECASE,
    )
    match = section_pattern.search(body)
    section = match.group(1) if match else body

    # Extract numbered items
    numbered = re.findall(r"^\s*\d+[.)]\s*(.+)$", section, re.MULTILINE)
    if numbered:
        steps.extend([s.strip() for s in numbered if s.strip()])
        return steps

    # Extract bullet items
    bullets = re.findall(r"^\s*[-*]\s+(.+)$", section, re.MULTILINE)
    if bullets:
        steps.extend([s.strip() for s in bullets if s.strip()])
        return steps

    # Fallback: return non-empty lines from the section
    for line in section.strip().splitlines():
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("#"):
            steps.append(cleaned)

    return steps[:20]  # Cap at 20 steps


def _extract_expected_behavior(body: str) -> str:
    """Extract expected behavior from the issue body."""
    pattern = re.compile(
        r"(?:#{1,4}\s*)?(?:expected\s+behavior|expected\s+result|expected\s+outcome|should)\s*:?\s*\n([\s\S]*?)(?=\n#{1,4}\s|\n\n\n|\Z)",
        re.IGNORECASE,
    )
    match = pattern.search(body)
    if match:
        return match.group(1).strip()[:1000]
    return ""


def _determine_severity(labels: list[GiteaLabel], body: str) -> str:
    """Determine severity from issue labels, falling back to body analysis."""
    for label in labels:
        label_lower = label.name.lower().strip()
        if label_lower in SEVERITY_LABEL_MAP:
            return SEVERITY_LABEL_MAP[label_lower]

    # Heuristic: look for severity keywords in the body
    body_lower = body.lower()
    if any(kw in body_lower for kw in ["critical", "crash", "data loss", "security vulnerability", "rce"]):
        return "critical"
    if any(kw in body_lower for kw in ["high priority", "major", "production"]):
        return "high"
    if any(kw in body_lower for kw in ["minor", "cosmetic", "low priority"]):
        return "low"
    return "medium"


def _determine_task_type(labels: list[GiteaLabel], title: str, body: str) -> str:
    """Determine task type from issue labels, title, and body."""
    for label in labels:
        label_lower = label.name.lower().strip()
        if label_lower in TASK_TYPE_LABEL_MAP:
            return TASK_TYPE_LABEL_MAP[label_lower]

    # Heuristic: keyword analysis
    combined = (title + " " + body).lower()
    if any(kw in combined for kw in ["security", "vulnerability", "cve", "exploit", "injection"]):
        return "security-patch"
    if any(kw in combined for kw in ["slow", "performance", "latency", "memory leak", "timeout"]):
        return "performance-fix"
    if any(kw in combined for kw in ["dependency", "upgrade", "outdated", "deprecated"]):
        return "dependency-update"
    if any(kw in combined for kw in ["coverage", "untested", "add tests"]):
        return "test-coverage"
    return "bug-fix"


# ---------------------------------------------------------------------------
# HTTP helpers with retry
# ---------------------------------------------------------------------------

async def _request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    json: Any = None,
    headers: dict[str, str] | None = None,
    max_retries: int = MAX_RETRY_ATTEMPTS,
    timeout: float = 30.0,
) -> httpx.Response:
    """Execute an HTTP request with exponential backoff retry."""
    import asyncio

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = await client.request(
                method, url, json=json, headers=headers, timeout=timeout,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code < 500:
                raise
            logger.warning("http_retry", url=url, attempt=attempt + 1, status=exc.response.status_code)
        except httpx.TransportError as exc:
            last_exc = exc
            logger.warning("http_transport_retry", url=url, attempt=attempt + 1, error=str(exc))
        if attempt < max_retries - 1:
            await asyncio.sleep(min(RETRY_BACKOFF_BASE ** attempt, 30.0))
    raise last_exc  # type: ignore[misc]


async def _post_issue_comment(
    client: httpx.AsyncClient,
    repo_full_name: str,
    issue_number: int,
    body: str,
) -> None:
    """Post a comment on a Gitea issue."""
    url = f"{GITEA_URL}/api/v1/repos/{repo_full_name}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"token {GITEA_API_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        await _request_with_retry(
            client, "POST", url, json={"body": body}, headers=headers, timeout=15.0,
        )
        logger.info("issue_comment_posted", repo=repo_full_name, issue=issue_number)
    except Exception as exc:
        logger.error("issue_comment_failed", repo=repo_full_name, issue=issue_number, error=str(exc))
        WEBHOOKS_ERRORS.labels(stage="comment").inc()


async def _create_task_via_handler(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Create a task through the Task Handler service."""
    url = f"{TASK_HANDLER_URL}/tasks"
    try:
        resp = await _request_with_retry(
            client, "POST", url, json=payload, timeout=30.0,
        )
        return resp.json()
    except Exception as exc:
        logger.error("task_creation_failed", error=str(exc), payload_type=payload.get("task_type"))
        WEBHOOKS_ERRORS.labels(stage="task_creation").inc()
        raise


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

def _verify_gitea_signature(payload_bytes: bytes, signature: str | None) -> bool:
    """Verify the Gitea webhook HMAC-SHA256 signature."""
    if not GITEA_WEBHOOK_SECRET:
        # No secret configured; skip verification (dev mode)
        return True
    if not signature:
        return False

    expected = hmac.new(
        GITEA_WEBHOOK_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("issue_intake_starting", port=8002, task_handler=TASK_HANDLER_URL)
    yield
    logger.info("issue_intake_shutting_down")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SWE-Agent Issue Intake",
    description="System 17 -- AI Coder Beta: Gitea issue webhook processor for SWE-Agent",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health / Metrics
# ---------------------------------------------------------------------------

@app.get("/health", tags=["infrastructure"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {
        "status": "healthy",
        "service": "swe-agent-issue-intake",
        "system": "17",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/metrics", tags=["infrastructure"])
async def metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        content=generate_latest(registry).decode("utf-8"),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# Gitea Issue Webhook
# ---------------------------------------------------------------------------

@app.post("/webhook/gitea/issue", tags=["webhooks"])
async def webhook_gitea_issue(
    request: Request,
    x_gitea_signature: Optional[str] = Header(None, alias="X-Gitea-Signature"),
) -> JSONResponse:
    """
    Receive Gitea issue webhooks. Only processes issues that:
    1. Have the "swe-agent" label
    2. Are opened or labelled (action = "opened" or "labeled")

    Flow:
    - Parse issue title, body, labels, severity
    - Extract reproduction steps from issue body
    - Create task via task-handler POST /tasks
    - Post acknowledgement comment on the Gitea issue
    """
    start_time = time.monotonic()
    WEBHOOKS_RECEIVED.inc()

    # Read raw body for signature verification
    raw_body = await request.body()

    # Verify webhook signature
    if not _verify_gitea_signature(raw_body, x_gitea_signature):
        logger.warning("webhook_signature_invalid")
        WEBHOOKS_ERRORS.labels(stage="signature").inc()
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse the webhook payload
    try:
        import json
        payload_dict = json.loads(raw_body)
        webhook = GiteaIssueWebhook(**payload_dict)
    except Exception as exc:
        logger.error("webhook_parse_error", error=str(exc))
        WEBHOOKS_ERRORS.labels(stage="parse").inc()
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {exc}")

    # Only process "opened" and "labeled" actions
    if webhook.action not in ("opened", "labeled"):
        WEBHOOKS_SKIPPED.labels(reason="wrong_action").inc()
        logger.debug("webhook_skipped_action", action=webhook.action)
        return JSONResponse(
            status_code=200,
            content={"status": "skipped", "reason": f"Action '{webhook.action}' not handled"},
        )

    issue = webhook.issue
    repo = webhook.repository

    if not issue or not repo:
        WEBHOOKS_SKIPPED.labels(reason="missing_data").inc()
        return JSONResponse(
            status_code=200,
            content={"status": "skipped", "reason": "Missing issue or repository data"},
        )

    # Check for the "swe-agent" label
    label_names = [label.name.lower().strip() for label in issue.labels]
    if SWE_AGENT_LABEL not in label_names:
        WEBHOOKS_SKIPPED.labels(reason="no_swe_agent_label").inc()
        logger.debug(
            "webhook_skipped_no_label",
            issue_number=issue.number,
            labels=label_names,
        )
        return JSONResponse(
            status_code=200,
            content={"status": "skipped", "reason": "Issue does not have 'swe-agent' label"},
        )

    # Parse the issue for task creation
    reproduction_steps = _extract_reproduction_steps(issue.body)
    expected_behavior = _extract_expected_behavior(issue.body)
    severity = _determine_severity(issue.labels, issue.body)
    task_type = _determine_task_type(issue.labels, issue.title, issue.body)

    logger.info(
        "issue_accepted",
        issue_number=issue.number,
        repo=repo.full_name,
        task_type=task_type,
        severity=severity,
        reproduction_steps_count=len(reproduction_steps),
    )

    # Create the task via task-handler
    task_payload = {
        "task_type": task_type,
        "issue_url": issue.html_url,
        "repository": repo.full_name,
        "description": f"{issue.title}\n\n{issue.body[:2000]}",
        "reproduction_steps": reproduction_steps,
        "expected_behavior": expected_behavior,
        "severity": severity,
    }

    async with httpx.AsyncClient() as client:
        try:
            task_result = await _create_task_via_handler(client, task_payload)
            task_id = task_result.get("task_id", "unknown")
            TASKS_CREATED.labels(task_type=task_type).inc()

            # Post acknowledgement comment on the issue
            comment_body = (
                f"\U0001f50d **SWE-Agent investigating** \u2014 Task ID: `{task_id}`\n\n"
                f"| Detail | Value |\n"
                f"|--------|-------|\n"
                f"| **Task type** | `{task_type}` |\n"
                f"| **Severity** | `{severity}` |\n"
                f"| **Reproduction steps found** | {len(reproduction_steps)} |\n"
                f"| **Status** | `RECEIVED` |\n\n"
                f"I'll analyse the issue, attempt reproduction, identify the root cause, "
                f"implement a fix, and open a pull request. You'll be notified when the PR is ready.\n\n"
                f"Track progress: `GET /tasks/{task_id}`"
            )
            await _post_issue_comment(client, repo.full_name, issue.number, comment_body)

            WEBHOOKS_PROCESSED.inc()
            duration = time.monotonic() - start_time
            WEBHOOK_LATENCY.observe(duration)

            logger.info(
                "issue_intake_complete",
                task_id=task_id,
                issue_number=issue.number,
                repo=repo.full_name,
                duration_seconds=round(duration, 3),
            )

            return JSONResponse(
                status_code=201,
                content={
                    "status": "accepted",
                    "task_id": task_id,
                    "task_type": task_type,
                    "severity": severity,
                    "issue_number": issue.number,
                    "repository": repo.full_name,
                },
            )

        except Exception as exc:
            WEBHOOKS_ERRORS.labels(stage="processing").inc()
            duration = time.monotonic() - start_time
            WEBHOOK_LATENCY.observe(duration)

            logger.error(
                "issue_intake_failed",
                issue_number=issue.number,
                repo=repo.full_name,
                error=str(exc),
                duration_seconds=round(duration, 3),
            )

            # Post failure comment so the issue author knows
            async with httpx.AsyncClient() as comment_client:
                failure_comment = (
                    f"\u26a0\ufe0f **SWE-Agent** encountered an error while processing this issue.\n\n"
                    f"Error: `{str(exc)[:300]}`\n\n"
                    f"A human reviewer has been notified. You can also try removing and re-adding "
                    f"the `swe-agent` label to retry."
                )
                await _post_issue_comment(comment_client, repo.full_name, issue.number, failure_comment)

            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "error": str(exc)[:500],
                    "issue_number": issue.number,
                    "repository": repo.full_name,
                },
            )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        log_level="info",
        access_log=True,
    )
