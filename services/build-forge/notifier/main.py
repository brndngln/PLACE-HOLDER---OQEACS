"""
System 35 — Build Forge: Notifier Service
Omni Quantum Elite AI Coding System

FastAPI service that receives Woodpecker CI webhook events, formats them as
Mattermost messages, and dispatches Omi haptic feedback signals.

Endpoints:
  POST /webhook/woodpecker  — receive pipeline events
  GET  /health              — liveness probe
  GET  /metrics             — Prometheus-compatible metrics
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

# =============================================================================
# Structured Logging
# =============================================================================
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.get_config().get("min_level", 0)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("build-forge-notifier")

# =============================================================================
# Configuration
# =============================================================================
MATTERMOST_WEBHOOK_URL = os.environ.get(
    "MATTERMOST_WEBHOOK_URL",
    "http://omni-mattermost-webhook:8066/hooks/builds",
)
MATTERMOST_DEPLOY_WEBHOOK_URL = os.environ.get(
    "MATTERMOST_DEPLOY_WEBHOOK_URL",
    "http://omni-mattermost-webhook:8066/hooks/deployments",
)
OMI_BRIDGE_URL = os.environ.get(
    "OMI_BRIDGE_URL",
    "http://omni-omi-bridge:9700",
)
WOODPECKER_URL = os.environ.get(
    "WOODPECKER_URL",
    "http://omni-woodpecker-server:8000",
)
LANGFUSE_URL = os.environ.get(
    "LANGFUSE_URL",
    "http://omni-langfuse:3000",
)
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8001"))

# =============================================================================
# Metrics Storage
# =============================================================================


class MetricsCollector:
    """Thread-safe in-memory Prometheus-style metrics collector."""

    def __init__(self) -> None:
        self._pipeline_runs: dict[str, int] = {}
        self._pipeline_durations: dict[str, list[float]] = {}
        self._webhook_received_total: int = 0
        self._webhook_errors_total: int = 0
        self._notification_sent_total: int = 0
        self._notification_failed_total: int = 0
        self._start_time: float = time.time()

    def inc_pipeline_run(self, repo: str, status: str) -> None:
        key = f'{repo}:{status}'
        self._pipeline_runs[key] = self._pipeline_runs.get(key, 0) + 1

    def observe_duration(self, repo: str, stage: str, duration: float) -> None:
        key = f'{repo}:{stage}'
        if key not in self._pipeline_durations:
            self._pipeline_durations[key] = []
        self._pipeline_durations[key].append(duration)

    def inc_webhook_received(self) -> None:
        self._webhook_received_total += 1

    def inc_webhook_error(self) -> None:
        self._webhook_errors_total += 1

    def inc_notification_sent(self) -> None:
        self._notification_sent_total += 1

    def inc_notification_failed(self) -> None:
        self._notification_failed_total += 1

    def render_prometheus(self) -> str:
        lines: list[str] = []
        uptime = time.time() - self._start_time

        lines.append("# HELP build_forge_notifier_uptime_seconds Time since service start.")
        lines.append("# TYPE build_forge_notifier_uptime_seconds gauge")
        lines.append(f"build_forge_notifier_uptime_seconds {uptime:.2f}")
        lines.append("")

        lines.append("# HELP pipeline_runs_total Total pipeline runs by repo and status.")
        lines.append("# TYPE pipeline_runs_total counter")
        for key, count in sorted(self._pipeline_runs.items()):
            repo, status = key.rsplit(":", 1)
            lines.append(f'pipeline_runs_total{{repo="{repo}",status="{status}"}} {count}')
        lines.append("")

        lines.append("# HELP pipeline_duration_seconds Pipeline stage duration in seconds.")
        lines.append("# TYPE pipeline_duration_seconds summary")
        for key, durations in sorted(self._pipeline_durations.items()):
            repo, stage = key.rsplit(":", 1)
            total = sum(durations)
            count = len(durations)
            lines.append(
                f'pipeline_duration_seconds_sum{{repo="{repo}",stage="{stage}"}} {total:.3f}'
            )
            lines.append(
                f'pipeline_duration_seconds_count{{repo="{repo}",stage="{stage}"}} {count}'
            )
        lines.append("")

        lines.append("# HELP webhook_received_total Total webhook events received.")
        lines.append("# TYPE webhook_received_total counter")
        lines.append(f"webhook_received_total {self._webhook_received_total}")
        lines.append("")

        lines.append("# HELP webhook_errors_total Total webhook processing errors.")
        lines.append("# TYPE webhook_errors_total counter")
        lines.append(f"webhook_errors_total {self._webhook_errors_total}")
        lines.append("")

        lines.append("# HELP notification_sent_total Total notifications sent.")
        lines.append("# TYPE notification_sent_total counter")
        lines.append(f"notification_sent_total {self._notification_sent_total}")
        lines.append("")

        lines.append("# HELP notification_failed_total Total failed notification attempts.")
        lines.append("# TYPE notification_failed_total counter")
        lines.append(f"notification_failed_total {self._notification_failed_total}")
        lines.append("")

        return "\n".join(lines) + "\n"


metrics = MetricsCollector()

# =============================================================================
# HTTP Client
# =============================================================================
http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — create and close shared HTTP client."""
    global http_client
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
    )
    logger.info(
        "notifier_started",
        port=SERVICE_PORT,
        mattermost_url=MATTERMOST_WEBHOOK_URL,
        omi_url=OMI_BRIDGE_URL,
    )
    yield
    await http_client.aclose()
    logger.info("notifier_stopped")


# =============================================================================
# FastAPI Application
# =============================================================================
app = FastAPI(
    title="Build Forge Notifier",
    description="Woodpecker CI notification relay for Mattermost and Omi Bridge",
    version="1.0.0",
    lifespan=lifespan,
)

# =============================================================================
# Models
# =============================================================================


class PipelineStatus(str, Enum):
    success = "success"
    failure = "failure"
    error = "error"
    running = "running"
    pending = "pending"
    skipped = "skipped"
    killed = "killed"


class PipelineEvent(str, Enum):
    build = "build"
    deploy = "deploy"
    deploy_staging = "deploy_staging"
    deploy_production = "deploy_production"
    approval = "approval"
    rollback = "rollback"


class WoodpeckerWebhook(BaseModel):
    repo: str = Field(..., description="Repository name (owner/repo)")
    commit: str = Field(..., description="Short commit SHA")
    branch: str = Field(default="main", description="Branch name")
    pipeline: str = Field(default="0", description="Pipeline number")
    author: str = Field(default="unknown", description="Commit author")
    status: PipelineStatus = Field(..., description="Pipeline status")
    event: PipelineEvent = Field(default=PipelineEvent.build, description="Event type")
    message: str = Field(default="", description="Commit message")
    duration_seconds: float = Field(default=0.0, description="Pipeline duration in seconds")
    stage: str = Field(default="", description="Current pipeline stage")
    link: str = Field(default="", description="Direct link to pipeline")
    started_at: str = Field(default="", description="Pipeline start timestamp (ISO)")
    finished_at: str = Field(default="", description="Pipeline finish timestamp (ISO)")


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "build-forge-notifier"
    version: str = "1.0.0"
    uptime_seconds: float = 0.0


# =============================================================================
# Mattermost Message Templates
# =============================================================================


def format_build_success(event: WoodpeckerWebhook) -> dict[str, Any]:
    """Format a successful build notification for #builds."""
    pipeline_link = event.link or (
        f"{WOODPECKER_URL}/repos/{event.repo}/pipeline/{event.pipeline}"
    )
    duration_str = (
        f"{event.duration_seconds:.0f}s" if event.duration_seconds > 0 else "N/A"
    )

    return {
        "channel": "builds",
        "username": "cicdbot",
        "icon_url": "https://woodpecker-ci.org/img/logo.svg",
        "text": (
            f":white_check_mark: **Pipeline #{event.pipeline} Passed** "
            f"| `{event.repo}` on `{event.branch}`\n"
            f"| Commit | Author | Duration |\n"
            f"|--------|--------|----------|\n"
            f"| `{event.commit}` | {event.author} | {duration_str} |\n"
            f"\n[View Pipeline]({pipeline_link})"
        ),
    }


def format_build_failure(event: WoodpeckerWebhook) -> dict[str, Any]:
    """Format a failed build notification for #builds."""
    pipeline_link = event.link or (
        f"{WOODPECKER_URL}/repos/{event.repo}/pipeline/{event.pipeline}"
    )
    duration_str = (
        f"{event.duration_seconds:.0f}s" if event.duration_seconds > 0 else "N/A"
    )
    stage_info = f" at stage `{event.stage}`" if event.stage else ""

    return {
        "channel": "builds",
        "username": "cicdbot",
        "icon_url": "https://woodpecker-ci.org/img/logo.svg",
        "text": (
            f":x: **Pipeline #{event.pipeline} Failed{stage_info}** "
            f"| `{event.repo}` on `{event.branch}`\n"
            f"| Commit | Author | Duration |\n"
            f"|--------|--------|----------|\n"
            f"| `{event.commit}` | {event.author} | {duration_str} |\n"
            f"\n[View Pipeline]({pipeline_link})"
        ),
    }


def format_build_error(event: WoodpeckerWebhook) -> dict[str, Any]:
    """Format an error build notification for #builds."""
    pipeline_link = event.link or (
        f"{WOODPECKER_URL}/repos/{event.repo}/pipeline/{event.pipeline}"
    )

    return {
        "channel": "builds",
        "username": "cicdbot",
        "icon_url": "https://woodpecker-ci.org/img/logo.svg",
        "text": (
            f":warning: **Pipeline #{event.pipeline} Error** "
            f"| `{event.repo}` on `{event.branch}`\n"
            f"Commit: `{event.commit}` by {event.author}\n"
            f"The pipeline encountered an infrastructure error.\n"
            f"[View Pipeline]({pipeline_link})"
        ),
    }


def format_deploy_event(event: WoodpeckerWebhook) -> dict[str, Any]:
    """Format a deployment notification for #deployments."""
    pipeline_link = event.link or (
        f"{WOODPECKER_URL}/repos/{event.repo}/pipeline/{event.pipeline}"
    )

    env_name = "Production" if "production" in event.event.value else "Staging"
    status_icon = ":white_check_mark:" if event.status == PipelineStatus.success else ":x:"

    return {
        "channel": "deployments",
        "username": "cicdbot",
        "icon_url": "https://woodpecker-ci.org/img/logo.svg",
        "text": (
            f"{status_icon} **{env_name} Deployment "
            f"{'Succeeded' if event.status == PipelineStatus.success else 'Failed'}** "
            f"| `{event.repo}`\n"
            f"| Commit | Author | Branch | Pipeline |\n"
            f"|--------|--------|--------|----------|\n"
            f"| `{event.commit}` | {event.author} | `{event.branch}` | "
            f"[#{event.pipeline}]({pipeline_link}) |\n"
        ),
    }


def format_approval_event(event: WoodpeckerWebhook) -> dict[str, Any]:
    """Format an approval request for #deployments."""
    pipeline_link = event.link or (
        f"{WOODPECKER_URL}/repos/{event.repo}/pipeline/{event.pipeline}"
    )

    return {
        "channel": "deployments",
        "username": "cicdbot",
        "icon_url": "https://woodpecker-ci.org/img/logo.svg",
        "text": (
            f":lock: **Production Approval Required** | `{event.repo}`\n\n"
            f"| Field | Value |\n"
            f"|-------|-------|\n"
            f"| **Repository** | `{event.repo}` |\n"
            f"| **Branch** | `{event.branch}` |\n"
            f"| **Commit** | `{event.commit}` |\n"
            f"| **Author** | {event.author} |\n"
            f"| **Pipeline** | #{event.pipeline} |\n\n"
            f"[Approve Deployment]({pipeline_link})"
        ),
    }


# =============================================================================
# Omi Haptic Patterns
# =============================================================================

OMI_HAPTIC_PATTERNS: dict[str, dict[str, Any]] = {
    "build-complete": {
        "pattern": "build-complete",
        "intensity": 0.6,
        "duration_ms": 500,
        "description": "Gentle pulse indicating successful build",
    },
    "test-failure": {
        "pattern": "test-failure",
        "intensity": 0.9,
        "duration_ms": 1000,
        "description": "Strong alert pulse indicating test failure",
    },
    "deploy-success": {
        "pattern": "deploy-success",
        "intensity": 0.7,
        "duration_ms": 750,
        "description": "Sustained pulse indicating successful deployment",
    },
    "deploy-failure": {
        "pattern": "deploy-failure",
        "intensity": 1.0,
        "duration_ms": 1500,
        "description": "Urgent repeated pulse indicating deployment failure",
    },
}


def get_haptic_pattern(event: WoodpeckerWebhook) -> str:
    """Determine the Omi haptic pattern based on pipeline event and status."""
    if event.event in (
        PipelineEvent.deploy,
        PipelineEvent.deploy_staging,
        PipelineEvent.deploy_production,
    ):
        if event.status == PipelineStatus.success:
            return "deploy-success"
        return "deploy-failure"

    if event.status == PipelineStatus.success:
        return "build-complete"
    return "test-failure"


# =============================================================================
# Notification Dispatch
# =============================================================================


async def send_mattermost_notification(payload: dict[str, Any], is_deploy: bool = False) -> bool:
    """Send a formatted message to Mattermost via incoming webhook."""
    webhook_url = MATTERMOST_DEPLOY_WEBHOOK_URL if is_deploy else MATTERMOST_WEBHOOK_URL

    try:
        resp = await http_client.post(webhook_url, json=payload)
        if resp.status_code < 300:
            metrics.inc_notification_sent()
            logger.info(
                "mattermost_notification_sent",
                channel=payload.get("channel", "unknown"),
                status_code=resp.status_code,
            )
            return True
        logger.warning(
            "mattermost_notification_failed",
            channel=payload.get("channel", "unknown"),
            status_code=resp.status_code,
            response=resp.text[:200],
        )
        metrics.inc_notification_failed()
        return False
    except Exception as exc:
        logger.error(
            "mattermost_notification_error",
            error=str(exc),
            webhook_url=webhook_url,
        )
        metrics.inc_notification_failed()
        return False


async def send_omi_haptic(event: WoodpeckerWebhook) -> bool:
    """Send haptic feedback signal to the Omi Bridge."""
    pattern_name = get_haptic_pattern(event)
    pattern = OMI_HAPTIC_PATTERNS.get(pattern_name, OMI_HAPTIC_PATTERNS["build-complete"])

    omi_payload = {
        "type": "haptic",
        "source": "build-forge-notifier",
        "pattern": pattern["pattern"],
        "intensity": pattern["intensity"],
        "duration_ms": pattern["duration_ms"],
        "metadata": {
            "repo": event.repo,
            "pipeline": event.pipeline,
            "status": event.status.value,
            "event": event.event.value,
            "commit": event.commit,
            "author": event.author,
        },
    }

    try:
        resp = await http_client.post(
            f"{OMI_BRIDGE_URL}/api/haptic",
            json=omi_payload,
        )
        if resp.status_code < 300:
            logger.info(
                "omi_haptic_sent",
                pattern=pattern_name,
                repo=event.repo,
                status=event.status.value,
            )
            return True
        logger.warning(
            "omi_haptic_failed",
            pattern=pattern_name,
            status_code=resp.status_code,
        )
        return False
    except Exception as exc:
        logger.warning(
            "omi_haptic_error",
            error=str(exc),
            pattern=pattern_name,
        )
        return False


# =============================================================================
# Routes
# =============================================================================


@app.post("/webhook/woodpecker")
async def receive_woodpecker_webhook(event: WoodpeckerWebhook) -> dict[str, Any]:
    """
    Receive a Woodpecker CI pipeline webhook event.

    Formats the event into a Mattermost message and dispatches it to the
    appropriate channel (#builds for build events, #deployments for deploy
    events). Also sends an Omi haptic feedback signal.
    """
    metrics.inc_webhook_received()

    logger.info(
        "webhook_received",
        repo=event.repo,
        pipeline=event.pipeline,
        status=event.status.value,
        event=event.event.value,
        commit=event.commit,
        author=event.author,
    )

    # Record metrics
    metrics.inc_pipeline_run(event.repo, event.status.value)
    if event.duration_seconds > 0:
        stage = event.stage if event.stage else "total"
        metrics.observe_duration(event.repo, stage, event.duration_seconds)

    # Determine message format and target channel
    is_deploy = event.event in (
        PipelineEvent.deploy,
        PipelineEvent.deploy_staging,
        PipelineEvent.deploy_production,
        PipelineEvent.rollback,
    )

    mattermost_payload: dict[str, Any] | None = None

    if event.event == PipelineEvent.approval:
        mattermost_payload = format_approval_event(event)
        is_deploy = True
    elif is_deploy:
        mattermost_payload = format_deploy_event(event)
    elif event.status == PipelineStatus.success:
        mattermost_payload = format_build_success(event)
    elif event.status == PipelineStatus.failure:
        mattermost_payload = format_build_failure(event)
    elif event.status == PipelineStatus.error:
        mattermost_payload = format_build_error(event)
    elif event.status == PipelineStatus.killed:
        mattermost_payload = {
            "channel": "builds",
            "username": "cicdbot",
            "icon_url": "https://woodpecker-ci.org/img/logo.svg",
            "text": (
                f":stop_sign: **Pipeline #{event.pipeline} Killed** "
                f"| `{event.repo}` on `{event.branch}`\n"
                f"Commit: `{event.commit}` by {event.author}"
            ),
        }

    # Send Mattermost notification
    mattermost_sent = False
    if mattermost_payload is not None:
        mattermost_sent = await send_mattermost_notification(
            mattermost_payload, is_deploy=is_deploy
        )

    # Send Omi haptic feedback (only for terminal states)
    omi_sent = False
    if event.status in (
        PipelineStatus.success,
        PipelineStatus.failure,
        PipelineStatus.error,
    ):
        omi_sent = await send_omi_haptic(event)

    result = {
        "received": True,
        "repo": event.repo,
        "pipeline": event.pipeline,
        "status": event.status.value,
        "event": event.event.value,
        "mattermost_sent": mattermost_sent,
        "omi_haptic_sent": omi_sent,
    }

    logger.info("webhook_processed", **result)
    return result


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe endpoint."""
    return HealthResponse(
        status="healthy",
        service="build-forge-notifier",
        version="1.0.0",
        uptime_seconds=round(time.time() - metrics._start_time, 2),
    )


@app.get("/metrics")
async def prometheus_metrics() -> Response:
    """Prometheus-compatible metrics endpoint."""
    return Response(
        content=metrics.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# =============================================================================
# Entrypoint
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level="info",
        access_log=True,
    )
