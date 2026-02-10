#!/usr/bin/env python3
"""
SYSTEM 15 — INTEGRATION HUB: GitHub Webhook Handler
Omni Quantum Elite AI Coding System — Communication & Workflow Layer

FastAPI endpoint receiving GitHub webhooks via Nango.  Routes events to
the appropriate Mattermost channels and triggers downstream actions
(knowledge re-ingestion, security alerts, competitive intelligence).

Requirements: fastapi, uvicorn, httpx, structlog, prometheus_client
"""

import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, Response
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
log = structlog.get_logger(service="github-handler", system="15", component="integration-hub")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WEBHOOK_ROUTER_URL = os.environ.get("WEBHOOK_ROUTER_URL", "http://omni-webhook-router:8066")
KNOWLEDGE_INGESTOR_URL = os.environ.get("KNOWLEDGE_INGESTOR_URL", "http://omni-knowledge-ingestor:9400")
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

# Tracked repositories for knowledge re-ingestion
TRACKED_REPOS: set[str] = set(
    os.environ.get("TRACKED_REPOS", "omni-quantum/platform,omni-quantum/docs").split(",")
)
COMPETITOR_REPOS: set[str] = set(
    os.environ.get("COMPETITOR_REPOS", "").split(",")
) - {""}

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
GH_EVENTS_RECEIVED = Counter("github_events_received_total", "GitHub events received", ["event_type"])
GH_EVENTS_PROCESSED = Counter("github_events_processed_total", "GitHub events processed", ["event_type", "action"])
GH_ERRORS = Counter("github_handler_errors_total", "GitHub handler errors", ["event_type"])
GH_LATENCY = Histogram("github_handler_latency_seconds", "GitHub handler processing latency", ["event_type"])

# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Omni Quantum GitHub Handler",
    version="1.0.0",
    description="System 15 — GitHub webhook handler via Nango",
)


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not GITHUB_WEBHOOK_SECRET:
        return True  # Skip verification if no secret configured
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def post_to_webhook_router(
    client: httpx.AsyncClient,
    endpoint: str,
    payload: dict[str, Any],
) -> None:
    """Forward an event to the Communication Hub webhook router with retries."""
    retries = 3
    for attempt in range(retries):
        try:
            resp = await client.post(
                f"{WEBHOOK_ROUTER_URL}{endpoint}",
                json=payload,
                timeout=10.0,
            )
            resp.raise_for_status()
            return
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            if attempt < retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)
                continue
            log.error("webhook_router_failed", endpoint=endpoint, error=str(exc))


# ---------------------------------------------------------------------------
# Health / Metrics
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "github-handler", "system": "15"}


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")


# ---------------------------------------------------------------------------
# GitHub webhook endpoint
# ---------------------------------------------------------------------------
@app.post("/webhook/github")
async def handle_github_webhook(
    request: Request,
    x_github_event: str = Header(default="ping"),
    x_hub_signature_256: str = Header(default=""),
) -> dict[str, str]:
    """Process a GitHub webhook event.

    Supports: push, release, security_advisory, star, ping.
    """
    start = time.monotonic()
    raw_body = await request.body()

    # Verify signature
    if GITHUB_WEBHOOK_SECRET and not verify_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    body = await request.json()
    event_type = x_github_event
    GH_EVENTS_RECEIVED.labels(event_type=event_type).inc()

    async with httpx.AsyncClient() as client:
        try:
            if event_type == "ping":
                log.info("github_ping", zen=body.get("zen", ""))
                return {"status": "pong"}

            elif event_type == "push":
                await _handle_push(client, body)

            elif event_type == "release":
                await _handle_release(client, body)

            elif event_type == "security_advisory":
                await _handle_security_advisory(client, body)

            elif event_type == "star":
                await _handle_star(client, body)

            else:
                log.info("github_event_ignored", event_type=event_type)

            GH_EVENTS_PROCESSED.labels(event_type=event_type, action=body.get("action", "none")).inc()

        except Exception as exc:
            GH_ERRORS.labels(event_type=event_type).inc()
            log.error("github_event_failed", event_type=event_type, error=str(exc))
            raise

    GH_LATENCY.labels(event_type=event_type).observe(time.monotonic() - start)
    return {"status": "ok", "event": event_type}


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------
async def _handle_push(client: httpx.AsyncClient, body: dict[str, Any]) -> None:
    """Push to tracked repo → trigger knowledge re-ingestion."""
    repo_full = body.get("repository", {}).get("full_name", "")
    ref = body.get("ref", "")
    commits = body.get("commits", [])
    pusher = body.get("pusher", {}).get("name", "unknown")

    log.info("github_push", repo=repo_full, ref=ref, commits=len(commits), pusher=pusher)

    if repo_full in TRACKED_REPOS:
        # Trigger knowledge re-ingestion
        try:
            resp = await client.post(
                f"{KNOWLEDGE_INGESTOR_URL}/api/ingest",
                json={
                    "source": "github",
                    "repository": repo_full,
                    "ref": ref,
                    "changed_files": [
                        f for c in commits for f in c.get("added", []) + c.get("modified", [])
                    ],
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            log.info("knowledge_reingestion_triggered", repo=repo_full)
        except Exception as exc:
            log.warning("knowledge_reingestion_failed", repo=repo_full, error=str(exc))

        # Post to #knowledge
        await post_to_webhook_router(client, "/webhook/knowledge", {
            "source_name": f"GitHub: {repo_full}",
            "docs_ingested": len(commits),
            "embeddings_created": 0,
            "staleness_score": 0,
            "processing_time": "in progress",
            "status": "ingesting",
            "summary": f"Push by {pusher}: {len(commits)} commit(s) to {ref}",
        })


async def _handle_release(client: httpx.AsyncClient, body: dict[str, Any]) -> None:
    """New release → alert #knowledge + freshness update."""
    action = body.get("action", "")
    if action != "published":
        return

    release = body.get("release", {})
    repo_full = body.get("repository", {}).get("full_name", "")
    tag = release.get("tag_name", "unknown")
    name = release.get("name", tag)
    author = release.get("author", {}).get("login", "unknown")

    log.info("github_release", repo=repo_full, tag=tag, author=author)

    await post_to_webhook_router(client, "/webhook/knowledge", {
        "source_name": f"Release: {repo_full} {tag}",
        "docs_ingested": 1,
        "embeddings_created": 0,
        "staleness_score": 0,
        "processing_time": "N/A",
        "status": "new_release",
        "summary": f"New release **{name}** ({tag}) by {author}",
    })


async def _handle_security_advisory(client: httpx.AsyncClient, body: dict[str, Any]) -> None:
    """Security advisory → alert #security."""
    advisory = body.get("security_advisory", body)
    severity = advisory.get("severity", "medium")
    summary = advisory.get("summary", "Security advisory received")
    cve = advisory.get("cve_id", "N/A")
    references = advisory.get("references", [])
    ref_url = references[0].get("url", "") if references else ""

    log.info("github_security_advisory", severity=severity, cve=cve)

    await post_to_webhook_router(client, "/webhook/crowdsec", {
        "type": "security_advisory",
        "source": {"ip": f"GitHub Advisory: {cve}"},
        "decision": {"type": "alert", "duration": "N/A"},
        "scenario": summary,
        "reason": f"CVE: {cve} — Severity: {severity}",
        "dashboard_link": ref_url,
    })


async def _handle_star(client: httpx.AsyncClient, body: dict[str, Any]) -> None:
    """Star on tracked competitor repo → log competitive intelligence."""
    action = body.get("action", "")
    if action != "created":
        return

    repo_full = body.get("repository", {}).get("full_name", "")
    stars = body.get("repository", {}).get("stargazers_count", 0)
    sender = body.get("sender", {}).get("login", "unknown")

    if repo_full in COMPETITOR_REPOS:
        log.info("competitive_intelligence", repo=repo_full, stars=stars, new_stargazer=sender)
        # Log only — no Mattermost post for competitive intel


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8067, log_level="info")
