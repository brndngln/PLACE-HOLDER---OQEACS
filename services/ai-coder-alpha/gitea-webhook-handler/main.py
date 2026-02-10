#!/usr/bin/env python3
"""
SYSTEM 16 -- AI CODER ALPHA: Gitea Webhook Handler
Omni Quantum Elite AI Coding System -- AI Coding Agent Layer

FastAPI microservice (port 3002) that receives Gitea webhook events and
routes them to the OpenHands Task Orchestrator.  Handles issue creation
(label "openhands"), pull request auto-review, and push event processing.

Endpoints:
  POST /webhook/gitea/issue          -- new/updated issue with "openhands" label
  POST /webhook/gitea/pull-request   -- PR events for auto-review
  POST /webhook/gitea/push           -- push events for lightweight checks
  GET  /health                       -- liveness probe
  GET  /metrics                      -- Prometheus metrics

Requirements: fastapi, uvicorn, httpx, structlog, prometheus_client, pydantic, hmac
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest
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
log = structlog.get_logger(service="gitea-webhook-handler", system="16", component="ai-coder-alpha")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TASK_ORCHESTRATOR_URL = os.environ.get("TASK_ORCHESTRATOR_URL", "http://localhost:3001")
CODE_SCORER_URL = os.environ.get("CODE_SCORER_URL", "http://omni-code-scorer")
GITEA_URL = os.environ.get("GITEA_URL", "http://omni-gitea:3000")
GITEA_TOKEN = os.environ.get("GITEA_TOKEN", "")
GITEA_ORG = os.environ.get("GITEA_ORG", "omni-quantum")
MATTERMOST_WEBHOOK_URL = os.environ.get("MATTERMOST_WEBHOOK_URL", "")
WEBHOOK_SECRET = os.environ.get("GITEA_WEBHOOK_SECRET", "")
VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "")
OPENHANDS_BOT_USER = os.environ.get("OPENHANDS_BOT_USER", "openhands-bot")

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
WEBHOOKS_RECEIVED = Counter(
    "gitea_webhooks_received_total", "Total Gitea webhooks received",
    ["event_type"],
)
WEBHOOKS_PROCESSED = Counter(
    "gitea_webhooks_processed_total", "Gitea webhooks successfully processed",
    ["event_type", "action"],
)
WEBHOOK_ERRORS = Counter(
    "gitea_webhook_errors_total", "Gitea webhook processing errors",
    ["event_type"],
)
WEBHOOK_LATENCY = Histogram(
    "gitea_webhook_processing_seconds", "Webhook processing latency",
    ["event_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)
TASKS_CREATED = Counter(
    "gitea_webhook_tasks_created_total", "Tasks created from webhooks",
    ["task_type"],
)
REVIEWS_SUBMITTED = Counter(
    "gitea_webhook_reviews_submitted_total", "Code reviews submitted",
)

# ---------------------------------------------------------------------------
# In-memory tracking of pending tasks from issues
# ---------------------------------------------------------------------------
issue_task_map: dict[int, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class WebhookResponse(BaseModel):
    """Standard webhook response."""
    status: str
    trace_id: str
    message: str = ""
    task_id: Optional[str] = None


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
# Mattermost notification
# ---------------------------------------------------------------------------


async def notify_mattermost(
    client: httpx.AsyncClient,
    channel: str,
    text: str,
) -> None:
    """Post a notification to Mattermost."""
    if not MATTERMOST_WEBHOOK_URL:
        return
    try:
        await client.post(
            MATTERMOST_WEBHOOK_URL,
            json={
                "channel": channel,
                "username": "Gitea Webhook Handler",
                "icon_emoji": ":gear:",
                "text": text,
            },
            timeout=10.0,
        )
    except Exception as exc:
        log.warning("mattermost_notify_failed", channel=channel, error=str(exc))


# ---------------------------------------------------------------------------
# Gitea API helpers
# ---------------------------------------------------------------------------


async def gitea_post_comment(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    issue_number: int,
    body: str,
) -> None:
    """Post a comment on a Gitea issue or pull request."""
    headers = {
        "Authorization": f"token {GITEA_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        await http_request_with_retry(
            client, "POST",
            f"{GITEA_URL}/api/v1/repos/{owner}/{repo}/issues/{issue_number}/comments",
            headers=headers,
            json={"body": body},
            timeout=15.0,
        )
        log.info("gitea_comment_posted", repo=f"{owner}/{repo}", issue=issue_number)
    except Exception as exc:
        log.error("gitea_comment_failed", repo=f"{owner}/{repo}", issue=issue_number, error=str(exc))


async def gitea_post_review(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    event: str = "COMMENT",
) -> None:
    """Post a review on a Gitea pull request."""
    headers = {
        "Authorization": f"token {GITEA_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        await http_request_with_retry(
            client, "POST",
            f"{GITEA_URL}/api/v1/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            headers=headers,
            json={"body": body, "event": event},
            timeout=15.0,
        )
        log.info("gitea_review_posted", repo=f"{owner}/{repo}", pr=pr_number, event=event)
    except Exception as exc:
        log.error("gitea_review_failed", repo=f"{owner}/{repo}", pr=pr_number, error=str(exc))


async def gitea_get_pr_diff(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    pr_number: int,
) -> str:
    """Fetch the diff of a Gitea pull request."""
    headers = {
        "Authorization": f"token {GITEA_TOKEN}",
        "Accept": "text/plain",
    }
    try:
        resp = await http_request_with_retry(
            client, "GET",
            f"{GITEA_URL}/api/v1/repos/{owner}/{repo}/pulls/{pr_number}.diff",
            headers=headers,
            timeout=30.0,
        )
        return resp.text
    except Exception as exc:
        log.error("gitea_diff_failed", repo=f"{owner}/{repo}", pr=pr_number, error=str(exc))
        return ""


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Gitea webhook HMAC-SHA256 signature."""
    if not WEBHOOK_SECRET:
        return True  # No secret configured, skip verification
    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Issue label to task type mapping
# ---------------------------------------------------------------------------

LABEL_TASK_TYPE_MAP: dict[str, str] = {
    "feature": "feature-build",
    "feature-build": "feature-build",
    "enhancement": "feature-build",
    "bug": "bug-fix",
    "bug-fix": "bug-fix",
    "bugfix": "bug-fix",
    "fix": "bug-fix",
    "refactor": "refactor",
    "refactoring": "refactor",
    "cleanup": "refactor",
    "test": "test-gen",
    "test-gen": "test-gen",
    "testing": "test-gen",
    "tests": "test-gen",
}


def determine_task_type_from_labels(labels: list[dict[str, Any]]) -> str:
    """Determine task type from Gitea issue labels."""
    label_names = [lb.get("name", "").lower() for lb in labels]
    for label_name in label_names:
        if label_name in LABEL_TASK_TYPE_MAP:
            return LABEL_TASK_TYPE_MAP[label_name]
    return "feature-build"  # Default


def extract_language_from_labels(labels: list[dict[str, Any]]) -> str:
    """Extract programming language hint from labels."""
    language_labels = {"python", "javascript", "typescript", "go", "rust", "java", "ruby"}
    label_names = {lb.get("name", "").lower() for lb in labels}
    found = language_labels.intersection(label_names)
    return found.pop() if found else "python"


def extract_complexity_from_labels(labels: list[dict[str, Any]]) -> str:
    """Extract complexity hint from labels."""
    label_names = {lb.get("name", "").lower() for lb in labels}
    if "critical" in label_names:
        return "critical"
    if "high" in label_names or "complex" in label_names:
        return "high"
    if "low" in label_names or "simple" in label_names or "trivial" in label_names:
        return "low"
    return "medium"


def parse_issue_body(body: str) -> dict[str, Any]:
    """Parse structured fields from issue body.

    Supports markdown sections:
      ## Requirements
      - item 1
      - item 2

      ## Constraints
      - constraint 1

      ## Referenced Files
      - path/to/file.py

      ## Framework
      fastapi
    """
    result: dict[str, Any] = {
        "requirements": [],
        "constraints": [],
        "referenced_files": [],
        "framework": None,
    }

    current_section: str | None = None
    for line in body.split("\n"):
        stripped = line.strip()
        lower = stripped.lower()

        if lower.startswith("## requirements") or lower.startswith("### requirements"):
            current_section = "requirements"
            continue
        elif lower.startswith("## constraints") or lower.startswith("### constraints"):
            current_section = "constraints"
            continue
        elif lower.startswith("## referenced files") or lower.startswith("### referenced files"):
            current_section = "referenced_files"
            continue
        elif lower.startswith("## framework") or lower.startswith("### framework"):
            current_section = "framework"
            continue
        elif stripped.startswith("## ") or stripped.startswith("### "):
            current_section = None
            continue

        if current_section and stripped:
            item = stripped.lstrip("- *").strip()
            if not item:
                continue
            if current_section == "framework":
                result["framework"] = item
                current_section = None
            elif current_section in result and isinstance(result[current_section], list):
                result[current_section].append(item)

    return result


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    log.info("startup_complete", port=3002)
    yield
    log.info("shutdown")


app = FastAPI(
    title="AI Coder Alpha Gitea Webhook Handler",
    description="System 16 -- Gitea webhook handler for OpenHands task automation",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health / Metrics
# ---------------------------------------------------------------------------


@app.get("/health", tags=["infrastructure"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "gitea-webhook-handler", "system": "16"}


@app.get("/metrics", tags=["infrastructure"])
async def metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ---------------------------------------------------------------------------
# POST /webhook/gitea/issue
# ---------------------------------------------------------------------------


@app.post("/webhook/gitea/issue", tags=["webhooks"])
async def webhook_gitea_issue(
    request: Request,
    x_gitea_signature: Optional[str] = Header(None),
) -> WebhookResponse:
    """Handle Gitea issue webhooks.

    Only processes issues with the "openhands" label.  Parses the issue body
    to extract requirements, constraints, referenced files, and framework.
    Determines task_type from other labels.  Creates a task via the Task
    Orchestrator and comments on the issue with the task ID.
    """
    trace_id = str(uuid.uuid4())
    start_time = time.monotonic()
    WEBHOOKS_RECEIVED.labels(event_type="issue").inc()

    raw_body = await request.body()

    # Verify webhook signature
    if x_gitea_signature and not verify_webhook_signature(raw_body, x_gitea_signature):
        log.warning("webhook_signature_invalid", trace_id=trace_id, event="issue")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        WEBHOOK_ERRORS.labels(event_type="issue").inc()
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    action = payload.get("action", "")
    issue = payload.get("issue", {})
    issue_number = issue.get("number", 0)
    issue_title = issue.get("title", "")
    issue_body = issue.get("body", "")
    labels = issue.get("labels", [])
    repo = payload.get("repository", {})
    repo_name = repo.get("name", "")
    repo_full = repo.get("full_name", f"{GITEA_ORG}/{repo_name}")
    owner = repo_full.split("/")[0] if "/" in repo_full else GITEA_ORG

    log.info(
        "issue_webhook_received",
        trace_id=trace_id,
        action=action,
        issue=issue_number,
        repo=repo_full,
        labels=[lb.get("name", "") for lb in labels],
    )

    # Only process issues with the "openhands" label
    label_names = {lb.get("name", "").lower() for lb in labels}
    if "openhands" not in label_names:
        WEBHOOKS_PROCESSED.labels(event_type="issue", action="skipped_no_label").inc()
        latency = time.monotonic() - start_time
        WEBHOOK_LATENCY.labels(event_type="issue").observe(latency)
        return WebhookResponse(
            status="skipped",
            trace_id=trace_id,
            message="Issue does not have 'openhands' label",
        )

    # Only process opened/labeled actions
    if action not in ("opened", "labeled", "reopened"):
        WEBHOOKS_PROCESSED.labels(event_type="issue", action=f"skipped_{action}").inc()
        latency = time.monotonic() - start_time
        WEBHOOK_LATENCY.labels(event_type="issue").observe(latency)
        return WebhookResponse(
            status="skipped",
            trace_id=trace_id,
            message=f"Action '{action}' not processed",
        )

    # Check if we already have a task for this issue
    if issue_number in issue_task_map:
        existing = issue_task_map[issue_number]
        latency = time.monotonic() - start_time
        WEBHOOK_LATENCY.labels(event_type="issue").observe(latency)
        return WebhookResponse(
            status="duplicate",
            trace_id=trace_id,
            message=f"Task already exists for issue #{issue_number}",
            task_id=existing.get("task_id"),
        )

    # Determine task parameters
    task_type = determine_task_type_from_labels(labels)
    target_language = extract_language_from_labels(labels)
    complexity = extract_complexity_from_labels(labels)
    parsed_body = parse_issue_body(issue_body)

    # Create task via orchestrator
    task_payload = {
        "task_type": task_type,
        "description": f"{issue_title}\n\n{issue_body}",
        "repository": repo_name,
        "branch": "main",
        "target_language": target_language,
        "framework": parsed_body.get("framework"),
        "complexity": complexity,
        "referenced_files": parsed_body.get("referenced_files", []),
        "requirements": parsed_body.get("requirements", []),
        "constraints": parsed_body.get("constraints", []),
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await http_request_with_retry(
                client, "POST",
                f"{TASK_ORCHESTRATOR_URL}/tasks",
                json=task_payload,
                timeout=30.0,
            )
            task_result = resp.json()
            task_id = task_result.get("task_id", "unknown")
            working_branch = task_result.get("working_branch", "")

            # Store mapping
            issue_task_map[issue_number] = {
                "task_id": task_id,
                "repo_full": repo_full,
                "issue_number": issue_number,
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
            }

            TASKS_CREATED.labels(task_type=task_type).inc()
            log.info(
                "task_created_from_issue",
                trace_id=trace_id,
                task_id=task_id,
                issue=issue_number,
                task_type=task_type,
                repo=repo_full,
            )

            # Comment on the issue
            comment_body = (
                f"\U0001f916 **OpenHands is working on this issue!**\n\n"
                f"**Task ID:** `{task_id}`\n"
                f"**Task Type:** `{task_type}`\n"
                f"**Working Branch:** `{working_branch}`\n"
                f"**Language:** `{target_language}`\n"
                f"**Complexity:** `{complexity}`\n\n"
                f"I'll comment here again when the PR is ready for review.\n\n"
                f"---\n"
                f"*Powered by System 16 -- AI Coder Alpha (OpenHands)*"
            )
            await gitea_post_comment(client, owner, repo_name, issue_number, comment_body)

            # Start a background watcher to comment when task completes
            asyncio.create_task(
                _watch_task_completion(task_id, owner, repo_name, issue_number)
            )

            WEBHOOKS_PROCESSED.labels(event_type="issue", action="task_created").inc()

        except Exception as exc:
            WEBHOOK_ERRORS.labels(event_type="issue").inc()
            log.error(
                "task_creation_failed",
                trace_id=trace_id,
                issue=issue_number,
                error=str(exc),
            )

            await gitea_post_comment(
                client, owner, repo_name, issue_number,
                f"\u274c **OpenHands task creation failed**\n\nError: {str(exc)[:500]}\n\n"
                f"Please check the task orchestrator logs.\n\n"
                f"---\n*Powered by System 16 -- AI Coder Alpha (OpenHands)*",
            )

            latency = time.monotonic() - start_time
            WEBHOOK_LATENCY.labels(event_type="issue").observe(latency)
            return WebhookResponse(
                status="error",
                trace_id=trace_id,
                message=f"Task creation failed: {str(exc)[:200]}",
            )

    latency = time.monotonic() - start_time
    WEBHOOK_LATENCY.labels(event_type="issue").observe(latency)
    return WebhookResponse(
        status="ok",
        trace_id=trace_id,
        message=f"Task {task_id} created for issue #{issue_number}",
        task_id=task_id,
    )


async def _watch_task_completion(
    task_id: str,
    owner: str,
    repo_name: str,
    issue_number: int,
) -> None:
    """Background task that polls the orchestrator and comments when task completes."""
    poll_interval = 30  # seconds
    max_polls = 120  # 1 hour max
    async with httpx.AsyncClient() as client:
        for _ in range(max_polls):
            await asyncio.sleep(poll_interval)
            try:
                resp = await client.get(
                    f"{TASK_ORCHESTRATOR_URL}/tasks/{task_id}",
                    timeout=15.0,
                )
                if resp.status_code != 200:
                    continue
                task_data = resp.json()
                status = task_data.get("status", "")

                if status == "complete":
                    pr_url = task_data.get("pr_url", "")
                    score = task_data.get("code_score", {})
                    overall_score = score.get("overall", 0) if isinstance(score, dict) else 0
                    duration = task_data.get("duration_seconds", 0)

                    comment_body = (
                        f"\u2705 **OpenHands completed this task!**\n\n"
                        f"**PR:** [{pr_url}]({pr_url})\n"
                        f"**Quality Score:** {overall_score:.1f}/10\n"
                        f"**Duration:** {duration:.0f}s\n"
                        f"**Iterations:** {task_data.get('coding_iteration_count', 0)}\n\n"
                        f"Please review the PR and merge if satisfactory.\n\n"
                        f"---\n"
                        f"*Powered by System 16 -- AI Coder Alpha (OpenHands)*"
                    )
                    await gitea_post_comment(client, owner, repo_name, issue_number, comment_body)
                    log.info("task_completion_commented", task_id=task_id, issue=issue_number, pr_url=pr_url)
                    return

                if status in ("failed", "cancelled"):
                    error_msg = task_data.get("error_message", "Unknown error")
                    comment_body = (
                        f"\u274c **OpenHands task {status}**\n\n"
                        f"**Task ID:** `{task_id}`\n"
                        f"**Error:** {error_msg[:500]}\n\n"
                        f"You may re-open or re-label this issue to retry.\n\n"
                        f"---\n"
                        f"*Powered by System 16 -- AI Coder Alpha (OpenHands)*"
                    )
                    await gitea_post_comment(client, owner, repo_name, issue_number, comment_body)
                    log.info("task_failure_commented", task_id=task_id, issue=issue_number, status=status)
                    return

            except Exception as exc:
                log.debug("task_poll_error", task_id=task_id, error=str(exc))

    log.warning("task_watch_timeout", task_id=task_id, issue=issue_number)


# ---------------------------------------------------------------------------
# POST /webhook/gitea/pull-request
# ---------------------------------------------------------------------------


@app.post("/webhook/gitea/pull-request", tags=["webhooks"])
async def webhook_gitea_pull_request(
    request: Request,
    x_gitea_signature: Optional[str] = Header(None),
) -> WebhookResponse:
    """Handle Gitea pull request webhooks.

    Skips PRs created by the OpenHands bot.  If the PR has an "auto-review"
    label, submits it to Code Scorer for 10-dimension analysis and posts
    the review as a PR comment/review.
    """
    trace_id = str(uuid.uuid4())
    start_time = time.monotonic()
    WEBHOOKS_RECEIVED.labels(event_type="pull_request").inc()

    raw_body = await request.body()

    if x_gitea_signature and not verify_webhook_signature(raw_body, x_gitea_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        WEBHOOK_ERRORS.labels(event_type="pull_request").inc()
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    action = payload.get("action", "")
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number", 0)
    pr_title = pr.get("title", "")
    pr_user = pr.get("user", {}).get("login", "")
    labels = pr.get("labels", [])
    repo = payload.get("repository", {})
    repo_name = repo.get("name", "")
    repo_full = repo.get("full_name", f"{GITEA_ORG}/{repo_name}")
    owner = repo_full.split("/")[0] if "/" in repo_full else GITEA_ORG

    log.info(
        "pr_webhook_received",
        trace_id=trace_id,
        action=action,
        pr=pr_number,
        user=pr_user,
        repo=repo_full,
    )

    # Skip PRs from OpenHands bot
    if pr_user == OPENHANDS_BOT_USER:
        WEBHOOKS_PROCESSED.labels(event_type="pull_request", action="skipped_bot").inc()
        latency = time.monotonic() - start_time
        WEBHOOK_LATENCY.labels(event_type="pull_request").observe(latency)
        return WebhookResponse(
            status="skipped",
            trace_id=trace_id,
            message="Skipping PR from OpenHands bot",
        )

    # Only process opened/synchronized/labeled actions
    if action not in ("opened", "synchronize", "labeled", "reopened"):
        WEBHOOKS_PROCESSED.labels(event_type="pull_request", action=f"skipped_{action}").inc()
        latency = time.monotonic() - start_time
        WEBHOOK_LATENCY.labels(event_type="pull_request").observe(latency)
        return WebhookResponse(
            status="skipped",
            trace_id=trace_id,
            message=f"Action '{action}' not processed for PR",
        )

    # Check for auto-review label
    label_names = {lb.get("name", "").lower() for lb in labels}
    if "auto-review" not in label_names:
        WEBHOOKS_PROCESSED.labels(event_type="pull_request", action="skipped_no_auto_review").inc()
        latency = time.monotonic() - start_time
        WEBHOOK_LATENCY.labels(event_type="pull_request").observe(latency)
        return WebhookResponse(
            status="skipped",
            trace_id=trace_id,
            message="PR does not have 'auto-review' label",
        )

    # Fetch PR diff and submit to Code Scorer
    async with httpx.AsyncClient() as client:
        try:
            diff = await gitea_get_pr_diff(client, owner, repo_name, pr_number)
            if not diff:
                latency = time.monotonic() - start_time
                WEBHOOK_LATENCY.labels(event_type="pull_request").observe(latency)
                return WebhookResponse(
                    status="error",
                    trace_id=trace_id,
                    message="Could not fetch PR diff",
                )

            # Determine language from PR file extensions
            language = _detect_language_from_diff(diff)

            # Submit to Code Scorer
            score_resp = await http_request_with_retry(
                client, "POST",
                f"{CODE_SCORER_URL}/score",
                json={
                    "content": diff[:50000],  # Limit diff size
                    "content_type": "pull_request_diff",
                    "task_type": "review",
                    "language": language,
                    "context": f"PR #{pr_number}: {pr_title}",
                },
                timeout=30.0,
            )
            score_data = score_resp.json()
            overall_score = score_data.get("overall_score", 0)
            dimensions = score_data.get("dimensions", {})
            feedback = score_data.get("feedback", "No specific feedback.")

            # Build review comment
            dim_table = "| Dimension | Score |\n|-----------|-------|\n"
            for dim_name, dim_val in sorted(dimensions.items()):
                emoji = "\u2705" if isinstance(dim_val, (int, float)) and dim_val >= 7 else "\u26a0\ufe0f" if isinstance(dim_val, (int, float)) and dim_val >= 5 else "\u274c"
                dim_table += f"| {dim_name.replace('_', ' ').title()} | {emoji} {dim_val}/10 |\n"

            review_body = (
                f"## \U0001f916 AI Code Review\n\n"
                f"**Overall Score: {overall_score:.1f}/10**\n\n"
                f"### Dimension Scores\n\n"
                f"{dim_table}\n"
                f"### Feedback\n\n"
                f"{feedback}\n\n"
                f"---\n"
                f"*Automated review by System 16 -- AI Coder Alpha (Code Scorer)*"
            )

            # Determine review event type based on score
            if overall_score >= 8.0:
                review_event = "APPROVED"
            elif overall_score >= 5.0:
                review_event = "COMMENT"
            else:
                review_event = "REQUEST_CHANGES"

            await gitea_post_review(client, owner, repo_name, pr_number, review_body, review_event)
            REVIEWS_SUBMITTED.inc()

            log.info(
                "pr_review_submitted",
                trace_id=trace_id,
                pr=pr_number,
                score=overall_score,
                event=review_event,
                repo=repo_full,
            )

            WEBHOOKS_PROCESSED.labels(event_type="pull_request", action="reviewed").inc()

        except Exception as exc:
            WEBHOOK_ERRORS.labels(event_type="pull_request").inc()
            log.error(
                "pr_review_failed",
                trace_id=trace_id,
                pr=pr_number,
                error=str(exc),
            )
            latency = time.monotonic() - start_time
            WEBHOOK_LATENCY.labels(event_type="pull_request").observe(latency)
            return WebhookResponse(
                status="error",
                trace_id=trace_id,
                message=f"Review failed: {str(exc)[:200]}",
            )

    latency = time.monotonic() - start_time
    WEBHOOK_LATENCY.labels(event_type="pull_request").observe(latency)
    return WebhookResponse(
        status="ok",
        trace_id=trace_id,
        message=f"Review submitted for PR #{pr_number} (score: {overall_score:.1f})",
    )


def _detect_language_from_diff(diff: str) -> str:
    """Heuristically detect the primary language from a unified diff."""
    ext_counts: dict[str, int] = {}
    ext_lang_map: dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".cs": "csharp",
        ".swift": "swift",
        ".kt": "kotlin",
    }
    for line in diff.split("\n"):
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            path = line.split("/", 1)[-1] if "/" in line else line
            for ext, lang in ext_lang_map.items():
                if path.endswith(ext):
                    ext_counts[lang] = ext_counts.get(lang, 0) + 1
                    break

    if ext_counts:
        return max(ext_counts, key=ext_counts.get)  # type: ignore[arg-type]
    return "python"


# ---------------------------------------------------------------------------
# POST /webhook/gitea/push
# ---------------------------------------------------------------------------


@app.post("/webhook/gitea/push", tags=["webhooks"])
async def webhook_gitea_push(
    request: Request,
    x_gitea_signature: Optional[str] = Header(None),
) -> WebhookResponse:
    """Handle Gitea push webhooks.

    - Push to main: log the event.
    - Push to feature/fix branches: trigger lightweight checks.
    """
    trace_id = str(uuid.uuid4())
    start_time = time.monotonic()
    WEBHOOKS_RECEIVED.labels(event_type="push").inc()

    raw_body = await request.body()

    if x_gitea_signature and not verify_webhook_signature(raw_body, x_gitea_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        WEBHOOK_ERRORS.labels(event_type="push").inc()
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    ref = payload.get("ref", "")
    branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
    repo = payload.get("repository", {})
    repo_name = repo.get("name", "")
    repo_full = repo.get("full_name", f"{GITEA_ORG}/{repo_name}")
    commits = payload.get("commits", [])
    pusher = payload.get("pusher", {}).get("login", "unknown")
    commit_count = len(commits)

    log.info(
        "push_webhook_received",
        trace_id=trace_id,
        branch=branch,
        repo=repo_full,
        commits=commit_count,
        pusher=pusher,
    )

    if branch == "main" or branch == "master":
        # Log push to main
        commit_messages = [c.get("message", "")[:100] for c in commits[:5]]
        log.info(
            "push_to_main",
            trace_id=trace_id,
            repo=repo_full,
            commits=commit_count,
            messages=commit_messages,
        )
        WEBHOOKS_PROCESSED.labels(event_type="push", action="main_logged").inc()
        latency = time.monotonic() - start_time
        WEBHOOK_LATENCY.labels(event_type="push").observe(latency)
        return WebhookResponse(
            status="ok",
            trace_id=trace_id,
            message=f"Push to main logged: {commit_count} commit(s)",
        )

    # Feature/fix branches -- trigger lightweight checks
    if branch.startswith(("feature/", "fix/", "openhands/", "bugfix/", "refactor/")):
        async with httpx.AsyncClient() as client:
            try:
                # Trigger lightweight lint/security check via Code Scorer
                changed_files = []
                for commit in commits:
                    changed_files.extend(commit.get("added", []))
                    changed_files.extend(commit.get("modified", []))
                # Deduplicate
                changed_files = list(set(changed_files))

                if changed_files:
                    check_payload = {
                        "content": f"Branch: {branch}\nChanged files: {', '.join(changed_files[:50])}",
                        "content_type": "push_check",
                        "task_type": "lightweight-check",
                        "language": _detect_language_from_files(changed_files),
                        "context": f"Push to {branch} in {repo_full}",
                    }

                    try:
                        score_resp = await http_request_with_retry(
                            client, "POST",
                            f"{CODE_SCORER_URL}/score",
                            json=check_payload,
                            timeout=15.0,
                            max_retries=1,
                        )
                        score_data = score_resp.json()
                        overall = score_data.get("overall_score", 0)
                        log.info(
                            "push_lightweight_check",
                            trace_id=trace_id,
                            branch=branch,
                            score=overall,
                            files_checked=len(changed_files),
                        )
                    except Exception as check_exc:
                        log.debug("push_check_skipped", trace_id=trace_id, error=str(check_exc))

            except Exception as exc:
                log.warning("push_check_failed", trace_id=trace_id, error=str(exc))

        WEBHOOKS_PROCESSED.labels(event_type="push", action="branch_checked").inc()
        latency = time.monotonic() - start_time
        WEBHOOK_LATENCY.labels(event_type="push").observe(latency)
        return WebhookResponse(
            status="ok",
            trace_id=trace_id,
            message=f"Push to {branch} processed: {commit_count} commit(s), {len(changed_files)} file(s) checked",
        )

    # Other branches -- just log
    WEBHOOKS_PROCESSED.labels(event_type="push", action="logged").inc()
    latency = time.monotonic() - start_time
    WEBHOOK_LATENCY.labels(event_type="push").observe(latency)
    return WebhookResponse(
        status="ok",
        trace_id=trace_id,
        message=f"Push to {branch} logged: {commit_count} commit(s)",
    )


def _detect_language_from_files(files: list[str]) -> str:
    """Detect primary language from a list of file paths."""
    ext_lang: dict[str, str] = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby",
    }
    counts: dict[str, int] = {}
    for f in files:
        for ext, lang in ext_lang.items():
            if f.endswith(ext):
                counts[lang] = counts.get(lang, 0) + 1
                break
    if counts:
        return max(counts, key=counts.get)  # type: ignore[arg-type]
    return "python"


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3002,
        log_level="info",
        access_log=True,
    )
