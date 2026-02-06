"""
Omni Quantum Elite — Uptime Kuma Webhook Relay
Receives webhooks from Uptime Kuma and forwards to Mattermost + Omi.
"""

import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request
from prometheus_client import Counter, generate_latest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("uptime-webhook-relay")

app = FastAPI(title="Uptime Webhook Relay", version="1.0.0")

MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK", "")
OMI_WEBHOOK = os.getenv("OMI_WEBHOOK_URL", "")

alerts_relayed = Counter("uptime_alerts_relayed_total", "Alerts relayed", ["type", "status"])


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.post("/webhook/uptime-kuma")
async def receive_uptime_kuma(request: Request):
    """Receive Uptime Kuma webhook and forward to Mattermost + Omi."""
    body = await request.json()
    monitor = body.get("monitor", {})
    heartbeat = body.get("heartbeat", {})
    msg_text = body.get("msg", "Unknown event")

    name = monitor.get("name", "Unknown")
    url = monitor.get("url", "")
    status = heartbeat.get("status", 0)
    ping = heartbeat.get("ping", "N/A")
    status_text = "UP ✅" if status == 1 else "DOWN 🔴"

    alerts_relayed.labels(type="uptime-kuma", status=status_text).inc()

    # Mattermost notification
    if MATTERMOST_WEBHOOK:
        icon = "✅" if status == 1 else "🔴"
        payload = {
            "username": "Uptime Monitor",
            "icon_emoji": ":satellite:",
            "text": (
                f"### {icon} {name}: {status_text}\n"
                f"| Field | Value |\n|---|---|\n"
                f"| Service | `{name}` |\n"
                f"| URL | {url} |\n"
                f"| Status | **{status_text}** |\n"
                f"| Ping | {ping}ms |\n"
                f"| Message | {msg_text} |\n"
                f"| Time | {datetime.now(timezone.utc).isoformat()} |\n"
            ),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(MATTERMOST_WEBHOOK, json=payload)
            except Exception as e:
                logger.error(f"Mattermost relay failed: {e}")

    # Omi wearable notification (only for DOWN events)
    if OMI_WEBHOOK and status != 1:
        payload = {
            "type": "uptime_alert",
            "severity": "critical",
            "title": f"Service DOWN: {name}",
            "url": url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(OMI_WEBHOOK, json=payload)
            except Exception as e:
                logger.error(f"Omi relay failed: {e}")

    return {"status": "relayed", "monitor": name, "service_status": status_text}
