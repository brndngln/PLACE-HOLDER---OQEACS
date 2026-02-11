#!/usr/bin/env python3
"""
SYSTEM 10 — COMMUNICATION HUB: Central Webhook Router
Omni Quantum Elite AI Coding System — Communication & Workflow Layer

FastAPI service (port 8066) that receives webhooks from upstream systems,
formats messages using templates, and routes them to Mattermost channels
via bot tokens.  Critical alerts trigger Omi haptic feedback.

Requirements: fastapi, uvicorn, httpx, structlog, prometheus_client
"""

import json
import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog
import uvicorn
from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, generate_latest

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
log = structlog.get_logger(service="webhook-router", system="10", component="communication-hub")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MATTERMOST_URL = os.environ.get("MATTERMOST_URL", "http://omni-mattermost:8065")
OMI_BRIDGE_URL = os.environ.get("OMI_BRIDGE_URL", "http://omni-omi-bridge:9700")
VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "")
TEMPLATES_DIR = Path(os.environ.get(
    "TEMPLATES_DIR",
    str(Path(__file__).resolve().parent.parent / "message-templates"),
))

# Bot token env-var overrides (preferred over Vault for fast startup)
BOT_TOKENS: dict[str, str] = {
    "alertbot": os.environ.get("ALERTBOT_TOKEN", ""),
    "cicdbot": os.environ.get("CICDBOT_TOKEN", ""),
    "aibot": os.environ.get("AIBOT_TOKEN", ""),
    "finbot": os.environ.get("FINBOT_TOKEN", ""),
    "omnibot": os.environ.get("OMNIBOT_TOKEN", ""),
}

# Channel → bot mapping
CHANNEL_BOT: dict[str, str] = {
    "omni-alerts": "alertbot",
    "omni-security": "alertbot",
    "omni-incidents": "alertbot",
    "omni-builds": "cicdbot",
    "omni-deployments": "cicdbot",
    "omni-reviews": "aibot",
    "omni-knowledge": "aibot",
    "omni-financial": "finbot",
    "omni-costs": "finbot",
    "omni-general": "omnibot",
}

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
WEBHOOKS_RECEIVED = Counter(
    "webhooks_received_total", "Webhooks received", ["source"],
)
WEBHOOKS_FORWARDED = Counter(
    "webhooks_forwarded_total", "Webhooks forwarded to Mattermost", ["channel"],
)
WEBHOOK_ERRORS = Counter(
    "webhook_errors_total", "Webhook processing errors", ["source"],
)
WEBHOOK_LATENCY = Histogram(
    "webhook_processing_seconds", "Webhook processing latency", ["source"],
)

# ---------------------------------------------------------------------------
# In-memory event history (last 100)
# ---------------------------------------------------------------------------
event_history: deque[dict[str, Any]] = deque(maxlen=100)

# ---------------------------------------------------------------------------
# Template loader
# ---------------------------------------------------------------------------
_template_cache: dict[str, dict[str, Any]] = {}


def load_template(name: str) -> dict[str, Any]:
    """Load and cache a message template JSON by name."""
    if name not in _template_cache:
        path = TEMPLATES_DIR / f"{name}.json"
        with open(path) as fh:
            _template_cache[name] = json.load(fh)
    return _template_cache[name]


def render_template(name: str, variables: dict[str, str]) -> dict[str, Any]:
    """Deep-render a template by replacing ``{{key}}`` placeholders."""
    raw = json.dumps(load_template(name))
    for key, value in variables.items():
        raw = raw.replace("{{" + key + "}}", str(value))
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Vault helpers
# ---------------------------------------------------------------------------
async def load_bot_tokens_from_vault(client: httpx.AsyncClient) -> None:
    """Attempt to fill missing bot tokens from Vault KV v2."""
    if not VAULT_TOKEN:
        log.warning("vault_token_missing", msg="No VAULT_TOKEN; relying on env bot tokens")
        return
    for bot_name in BOT_TOKENS:
        if BOT_TOKENS[bot_name]:
            continue
        try:
            resp = await client.get(
                f"{VAULT_ADDR}/v1/secret/data/mattermost/bots/{bot_name}",
                headers={"X-Vault-Token": VAULT_TOKEN},
                timeout=5.0,
            )
            resp.raise_for_status()
            BOT_TOKENS[bot_name] = resp.json()["data"]["data"]["token"]
            log.info("vault_bot_token_loaded", bot=bot_name)
        except Exception as exc:
            log.warning("vault_bot_token_failed", bot=bot_name, error=str(exc))

# Channel-ID cache
_channel_ids: dict[str, str] = {}


async def resolve_channel_id(client: httpx.AsyncClient, channel_name: str, bot_token: str) -> str:
    """Resolve a channel name to its Mattermost ID, caching the result."""
    if channel_name in _channel_ids:
        return _channel_ids[channel_name]
    # Need team ID first
    resp = await client.get(
        f"{MATTERMOST_URL}/api/v4/teams/name/omni-quantum",
        headers={"Authorization": f"Bearer {bot_token}"},
        timeout=5.0,
    )
    resp.raise_for_status()
    team_id = resp.json()["id"]
    resp = await client.get(
        f"{MATTERMOST_URL}/api/v4/teams/{team_id}/channels/name/{channel_name}",
        headers={"Authorization": f"Bearer {bot_token}"},
        timeout=5.0,
    )
    resp.raise_for_status()
    _channel_ids[channel_name] = resp.json()["id"]
    return _channel_ids[channel_name]


# ---------------------------------------------------------------------------
# Mattermost poster
# ---------------------------------------------------------------------------
async def post_to_channel(
    client: httpx.AsyncClient,
    channel: str,
    message: dict[str, Any],
    mention_channel: bool = False,
) -> None:
    """Post a formatted message to a Mattermost channel via bot token."""
    bot_name = CHANNEL_BOT.get(channel, "omnibot")
    token = BOT_TOKENS.get(bot_name)
    if not token:
        log.error("missing_bot_token", bot=bot_name, channel=channel)
        WEBHOOK_ERRORS.labels(source="internal").inc()
        return

    channel_id = await resolve_channel_id(client, channel, token)
    text = ""
    if mention_channel:
        text = "@channel "

    payload: dict[str, Any] = {
        "channel_id": channel_id,
        "message": text,
        "props": {"attachments": message.get("attachments", [])},
    }

    retries = 3
    for attempt in range(retries):
        try:
            resp = await client.post(
                f"{MATTERMOST_URL}/api/v4/posts",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=10.0,
            )
            resp.raise_for_status()
            WEBHOOKS_FORWARDED.labels(channel=channel).inc()
            log.info("message_posted", channel=channel, bot=bot_name)
            return
        except httpx.HTTPStatusError as exc:
            log.warning("post_retry", channel=channel, attempt=attempt + 1, status=exc.response.status_code)
            if attempt == retries - 1:
                raise
        except httpx.TransportError:
            if attempt == retries - 1:
                raise
            await _backoff(attempt)


async def _backoff(attempt: int) -> None:
    import asyncio
    await asyncio.sleep(min(2 ** attempt, 8))


# ---------------------------------------------------------------------------
# Omi haptic trigger
# ---------------------------------------------------------------------------
async def trigger_omi_haptic(client: httpx.AsyncClient, pattern: str, message: str | None = None) -> None:
    """Send a haptic alert to the Omi wearable bridge."""
    try:
        resp = await client.post(
            f"{OMI_BRIDGE_URL}/api/haptic",
            json={"pattern": pattern, "message": message},
            timeout=5.0,
        )
        resp.raise_for_status()
        log.info("omi_haptic_sent", pattern=pattern)
    except Exception as exc:
        log.warning("omi_haptic_failed", pattern=pattern, error=str(exc))


# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------
SEVERITY_COLORS = {
    "critical": "#FF0000",
    "warning": "#FFA500",
    "info": "#36A64F",
    "resolved": "#00FF00",
}


def determine_severity(payload: dict[str, Any], default: str = "info") -> str:
    """Extract severity from various payload formats."""
    for key in ("severity", "status", "level", "priority"):
        val = str(payload.get(key, "")).lower()
        if val in SEVERITY_COLORS:
            return val
    return default


def record_event(source: str, channel: str, severity: str, title: str, trace_id: str) -> None:
    """Append to in-memory event ring buffer."""
    event_history.append({
        "trace_id": trace_id,
        "source": source,
        "channel": channel,
        "severity": severity,
        "title": title,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient() as client:
        await load_bot_tokens_from_vault(client)
    log.info("startup_complete")
    yield
    log.info("shutdown")


app = FastAPI(
    title="Omni Quantum Webhook Router",
    version="1.0.0",
    description="System 10 — Communication Hub webhook router",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware — request metrics
# ---------------------------------------------------------------------------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    if request.url.path.startswith("/webhook/"):
        source = request.url.path.split("/webhook/")[-1]
        WEBHOOK_LATENCY.labels(source=source).observe(time.monotonic() - start)
    return response


# ---------------------------------------------------------------------------
# Health / Ready / Metrics
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "webhook-router", "system": "10"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness probe — checks that at least one bot token is available."""
    has_tokens = any(BOT_TOKENS.values())
    if not has_tokens:
        return {"status": "not_ready", "reason": "no bot tokens loaded"}
    return {"status": "ready"}


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")


@app.get("/webhook/history")
async def webhook_history() -> list[dict[str, Any]]:
    """Return last 100 webhook events."""
    return list(event_history)


# ---------------------------------------------------------------------------
# Webhook endpoints
# ---------------------------------------------------------------------------
@app.post("/webhook/prometheus")
async def webhook_prometheus(request: Request) -> dict[str, str]:
    """Receive Alertmanager webhook, post alerts to #alerts."""
    trace_id = str(uuid.uuid4())
    WEBHOOKS_RECEIVED.labels(source="prometheus").inc()
    body = await request.json()

    async with httpx.AsyncClient() as client:
        alerts = body.get("alerts", [body])
        for alert in alerts:
            severity = alert.get("labels", {}).get("severity", "warning")
            title = alert.get("labels", {}).get("alertname", "Prometheus Alert")
            msg = render_template("alert-critical", {
                "title": title,
                "service": alert.get("labels", {}).get("service", "unknown"),
                "message": alert.get("annotations", {}).get("summary", alert.get("annotations", {}).get("description", "")),
                "timestamp": alert.get("startsAt", datetime.now(tz=timezone.utc).isoformat()),
                "action": alert.get("annotations", {}).get("runbook_url", "Check Grafana dashboard"),
                "severity": severity,
                "source": "Alertmanager",
                "dashboard_link": alert.get("generatorURL", ""),
            })
            is_critical = severity == "critical"
            await post_to_channel(client, "omni-alerts", msg, mention_channel=is_critical)
            if is_critical:
                await trigger_omi_haptic(client, "critical", f"Critical alert: {title}")
            record_event("prometheus", "omni-alerts", severity, title, trace_id)
            log.info("prometheus_alert_processed", alert=title, severity=severity, trace_id=trace_id)

    return {"status": "ok", "trace_id": trace_id}


@app.post("/webhook/crowdsec")
async def webhook_crowdsec(request: Request) -> dict[str, str]:
    """Receive CrowdSec decisions, post to #security."""
    trace_id = str(uuid.uuid4())
    WEBHOOKS_RECEIVED.labels(source="crowdsec").inc()
    body = await request.json()

    async with httpx.AsyncClient() as client:
        event_type = body.get("type", "ban")
        source_ip = body.get("source", {}).get("ip", body.get("ip", "unknown"))
        msg = render_template("security-event", {
            "event_type": f"CrowdSec {event_type}",
            "source_ip_or_service": source_ip,
            "action_taken": body.get("decision", {}).get("type", event_type),
            "duration": body.get("decision", {}).get("duration", "N/A"),
            "reason": body.get("scenario", body.get("reason", "Automated detection")),
            "description": f"CrowdSec detected suspicious activity from {source_ip}",
            "dashboard_link": "",
        })
        await post_to_channel(client, "omni-security", msg)
        record_event("crowdsec", "omni-security", "warning", f"CrowdSec {event_type}: {source_ip}", trace_id)
        log.info("crowdsec_event_processed", event_type=event_type, source_ip=source_ip, trace_id=trace_id)

    return {"status": "ok", "trace_id": trace_id}


@app.post("/webhook/uptime-kuma")
async def webhook_uptime_kuma(request: Request) -> dict[str, str]:
    """Receive Uptime Kuma alerts, post to #alerts and #incidents."""
    trace_id = str(uuid.uuid4())
    WEBHOOKS_RECEIVED.labels(source="uptime-kuma").inc()
    body = await request.json()

    async with httpx.AsyncClient() as client:
        monitor = body.get("monitor", {})
        heartbeat = body.get("heartbeat", {})
        service_name = monitor.get("name", body.get("monitorName", "unknown"))
        status = "DOWN" if heartbeat.get("status") == 0 else "UP"
        severity = "critical" if status == "DOWN" else "resolved"

        msg = render_template("alert-critical", {
            "title": f"Service {status}: {service_name}",
            "service": service_name,
            "message": heartbeat.get("msg", f"{service_name} is {status}"),
            "timestamp": heartbeat.get("time", datetime.now(tz=timezone.utc).isoformat()),
            "action": "Investigate service health immediately" if status == "DOWN" else "Service recovered",
            "severity": severity,
            "source": "Uptime Kuma",
            "dashboard_link": "",
        })
        is_critical = status == "DOWN"
        await post_to_channel(client, "omni-alerts", msg, mention_channel=is_critical)
        await post_to_channel(client, "omni-incidents", msg, mention_channel=is_critical)
        if is_critical:
            await trigger_omi_haptic(client, "critical", f"Service DOWN: {service_name}")
        record_event("uptime-kuma", "omni-alerts", severity, f"Service {status}: {service_name}", trace_id)
        log.info("uptime_kuma_processed", service=service_name, status=status, trace_id=trace_id)

    return {"status": "ok", "trace_id": trace_id}


@app.post("/webhook/woodpecker")
async def webhook_woodpecker(request: Request) -> dict[str, str]:
    """Receive Woodpecker CI events, post to #builds."""
    trace_id = str(uuid.uuid4())
    WEBHOOKS_RECEIVED.labels(source="woodpecker").inc()
    body = await request.json()

    async with httpx.AsyncClient() as client:
        pipeline = body.get("pipeline", body)
        repo_name = body.get("repo", {}).get("full_name", body.get("repo_name", "unknown"))
        status = pipeline.get("status", "unknown")
        status_color = {"success": "#36A64F", "failure": "#FF0000", "running": "#FFA500"}.get(status, "#808080")

        started = pipeline.get("started", 0)
        finished = pipeline.get("finished", 0)
        duration = f"{finished - started}s" if finished and started else "N/A"

        msg = render_template("build-status", {
            "status_color": status_color,
            "status": status.upper(),
            "repo": repo_name,
            "branch": pipeline.get("branch", "unknown"),
            "commit_message": pipeline.get("message", "")[:200],
            "author": pipeline.get("author", "unknown"),
            "pipeline_stage": pipeline.get("event", "push"),
            "duration": duration,
            "ci_link": pipeline.get("link", ""),
        })
        await post_to_channel(client, "omni-builds", msg)
        record_event("woodpecker", "omni-builds", "info", f"Build {status}: {repo_name}", trace_id)
        log.info("woodpecker_processed", repo=repo_name, status=status, trace_id=trace_id)

    return {"status": "ok", "trace_id": trace_id}


@app.post("/webhook/code-scorer")
async def webhook_code_scorer(request: Request) -> dict[str, str]:
    """Receive Code Scorer quality scores, post to #reviews."""
    trace_id = str(uuid.uuid4())
    WEBHOOKS_RECEIVED.labels(source="code-scorer").inc()
    body = await request.json()

    async with httpx.AsyncClient() as client:
        score = body.get("quality_score", 0)
        score_color = "#36A64F" if score >= 7 else "#FFA500" if score >= 5 else "#FF0000"
        gate_result = "PASSED" if body.get("passed", False) else "FAILED"
        dims = body.get("dimensions", {})

        msg = render_template("review-score", {
            "score_color": score_color,
            "task_id": body.get("task_id", "unknown"),
            "quality_score": str(score),
            "gate_result": gate_result,
            "review_link": body.get("review_link", ""),
            "dim_correctness": str(dims.get("correctness", "N/A")),
            "dim_maintainability": str(dims.get("maintainability", "N/A")),
            "dim_security": str(dims.get("security", "N/A")),
            "dim_performance": str(dims.get("performance", "N/A")),
            "dim_test_coverage": str(dims.get("test_coverage", "N/A")),
            "dim_documentation": str(dims.get("documentation", "N/A")),
        })
        await post_to_channel(client, "omni-reviews", msg)
        record_event("code-scorer", "omni-reviews", "info", f"Review {gate_result}: {body.get('task_id', '')}", trace_id)
        log.info("code_scorer_processed", task_id=body.get("task_id"), score=score, passed=body.get("passed"), trace_id=trace_id)

    return {"status": "ok", "trace_id": trace_id}


@app.post("/webhook/coolify")
async def webhook_coolify(request: Request) -> dict[str, str]:
    """Receive Coolify deploy events, post to #deployments."""
    trace_id = str(uuid.uuid4())
    WEBHOOKS_RECEIVED.labels(source="coolify").inc()
    body = await request.json()

    async with httpx.AsyncClient() as client:
        status = body.get("status", "unknown")
        status_color = {"success": "#36A64F", "failed": "#FF0000", "running": "#FFA500"}.get(status, "#808080")
        app_name = body.get("app_name", body.get("name", "unknown"))

        msg = render_template("deploy-status", {
            "status_color": status_color,
            "status": status.upper(),
            "app_name": app_name,
            "environment": body.get("environment", "production"),
            "version": body.get("version", body.get("commit", "latest")),
            "deploy_method": body.get("deploy_method", "rolling"),
            "duration": body.get("duration", "N/A"),
            "deploy_summary": body.get("message", f"Deployment {status} for {app_name}"),
            "deploy_link": body.get("url", ""),
            "rollback_link": body.get("rollback_url", ""),
        })
        is_failure = status == "failed"
        await post_to_channel(client, "omni-deployments", msg, mention_channel=is_failure)
        if is_failure:
            await trigger_omi_haptic(client, "test-failure", f"Deploy failed: {app_name}")
        record_event("coolify", "omni-deployments", "critical" if is_failure else "info", f"Deploy {status}: {app_name}", trace_id)
        log.info("coolify_processed", app=app_name, status=status, trace_id=trace_id)

    return {"status": "ok", "trace_id": trace_id}


@app.post("/webhook/financial")
async def webhook_financial(request: Request) -> dict[str, str]:
    """Receive financial service events, post to #financial."""
    trace_id = str(uuid.uuid4())
    WEBHOOKS_RECEIVED.labels(source="financial").inc()
    body = await request.json()

    async with httpx.AsyncClient() as client:
        days_overdue = body.get("days_overdue", 0)
        if days_overdue > 14:
            urgency_color = "#FF0000"
        elif days_overdue > 7:
            urgency_color = "#FF6600"
        elif days_overdue > 3:
            urgency_color = "#FFA500"
        else:
            urgency_color = "#36A64F"

        msg = render_template("financial-alert", {
            "urgency_color": urgency_color,
            "alert_type": body.get("alert_type", "Invoice Overdue"),
            "client_name": body.get("client_name", "Unknown"),
            "invoice_number": body.get("invoice_number", "N/A"),
            "currency": body.get("currency", "USD"),
            "amount": str(body.get("amount", "0.00")),
            "days_overdue": str(days_overdue),
            "action": body.get("action", "Follow up with client"),
            "summary": body.get("summary", ""),
            "invoice_link": body.get("invoice_link", ""),
        })
        mention = days_overdue > 7
        await post_to_channel(client, "omni-financial", msg, mention_channel=mention)
        record_event("financial", "omni-financial", "warning" if days_overdue > 3 else "info", f"Invoice overdue: {body.get('invoice_number', '')}", trace_id)
        log.info("financial_processed", invoice=body.get("invoice_number"), days_overdue=days_overdue, trace_id=trace_id)

    return {"status": "ok", "trace_id": trace_id}


@app.post("/webhook/knowledge")
async def webhook_knowledge(request: Request) -> dict[str, str]:
    """Receive knowledge ingestion events, post to #knowledge."""
    trace_id = str(uuid.uuid4())
    WEBHOOKS_RECEIVED.labels(source="knowledge").inc()
    body = await request.json()

    async with httpx.AsyncClient() as client:
        msg = render_template("knowledge-update", {
            "source_name": body.get("source_name", "unknown"),
            "docs_ingested": str(body.get("docs_ingested", 0)),
            "embeddings_created": str(body.get("embeddings_created", 0)),
            "staleness_score": str(body.get("staleness_score", 0)),
            "processing_time": body.get("processing_time", "N/A"),
            "status": body.get("status", "complete"),
            "summary": body.get("summary", "Knowledge base updated"),
            "source_link": body.get("source_link", ""),
        })
        await post_to_channel(client, "omni-knowledge", msg)
        record_event("knowledge", "omni-knowledge", "info", f"Knowledge update: {body.get('source_name', '')}", trace_id)
        log.info("knowledge_processed", source=body.get("source_name"), docs=body.get("docs_ingested"), trace_id=trace_id)

    return {"status": "ok", "trace_id": trace_id}


@app.post("/webhook/backup")
async def webhook_backup(request: Request) -> dict[str, str]:
    """Receive Backup Fortress events, post failures to #alerts."""
    trace_id = str(uuid.uuid4())
    WEBHOOKS_RECEIVED.labels(source="backup").inc()
    body = await request.json()

    async with httpx.AsyncClient() as client:
        status = body.get("status", "unknown")
        service = body.get("service", body.get("backup_target", "unknown"))
        is_failure = status in ("failed", "error")

        if is_failure:
            msg = render_template("alert-critical", {
                "title": f"Backup FAILED: {service}",
                "service": service,
                "message": body.get("error", body.get("message", "Backup operation failed")),
                "timestamp": body.get("timestamp", datetime.now(tz=timezone.utc).isoformat()),
                "action": "Check Backup Fortress dashboard and retry manually",
                "severity": "critical",
                "source": "Backup Fortress",
                "dashboard_link": "",
            })
            await post_to_channel(client, "omni-alerts", msg, mention_channel=True)
            await trigger_omi_haptic(client, "critical", f"Backup failed: {service}")
        record_event("backup", "omni-alerts", "critical" if is_failure else "info", f"Backup {status}: {service}", trace_id)
        log.info("backup_processed", service=service, status=status, trace_id=trace_id)

    return {"status": "ok", "trace_id": trace_id}


@app.post("/webhook/rotation")
async def webhook_rotation(request: Request) -> dict[str, str]:
    """Receive secret rotation events, post to #security."""
    trace_id = str(uuid.uuid4())
    WEBHOOKS_RECEIVED.labels(source="rotation").inc()
    body = await request.json()

    async with httpx.AsyncClient() as client:
        event_type = body.get("event", "secret_rotated")
        service = body.get("service", "unknown")
        msg = render_template("security-event", {
            "event_type": f"Secret Rotation: {event_type}",
            "source_ip_or_service": service,
            "action_taken": body.get("action", "Credentials rotated"),
            "duration": body.get("duration", "N/A"),
            "reason": body.get("reason", "Scheduled rotation"),
            "description": body.get("message", f"Secret rotation event for {service}"),
            "dashboard_link": "",
        })
        await post_to_channel(client, "omni-security", msg)
        record_event("rotation", "omni-security", "info", f"Secret rotation: {service}", trace_id)
        log.info("rotation_processed", service=service, event=event_type, trace_id=trace_id)

    return {"status": "ok", "trace_id": trace_id}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8066, log_level="info")
