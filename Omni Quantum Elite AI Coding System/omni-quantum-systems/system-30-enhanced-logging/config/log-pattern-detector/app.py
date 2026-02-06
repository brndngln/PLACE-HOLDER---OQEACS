"""
Omni Quantum Elite — Log Pattern Detector
Detects error pattern bursts, recurring failures, and anomalous log volumes
by querying Loki via LogQL.
"""

import asyncio
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from prometheus_client import Counter, Gauge, generate_latest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("log-pattern-detector")

app = FastAPI(title="Omni Quantum Log Pattern Detector", version="1.0.0")

LOKI_URL = os.getenv("LOKI_URL", "http://omni-loki:3100")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK", "")
OMI_WEBHOOK = os.getenv("OMI_WEBHOOK_URL", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "120"))
BURST_THRESHOLD = int(os.getenv("BURST_THRESHOLD", "100"))

patterns_detected = Counter("log_patterns_detected_total", "Patterns detected", ["pattern_type", "component"])
error_rate_gauge = Gauge("log_error_rate_per_min", "Error log rate per minute", ["component"])

DETECTION_QUERIES = [
    {
        "name": "error_burst",
        "description": "Error log burst detection",
        "query": 'sum by(component) (count_over_time({level=~"ERROR|CRITICAL"}[5m]))',
        "threshold": BURST_THRESHOLD,
        "severity": "warning",
    },
    {
        "name": "auth_failures",
        "description": "Authentication failure spike",
        "query": 'sum by(component) (count_over_time({component="authentik"} |= "failed" [5m]))',
        "threshold": 20,
        "severity": "critical",
    },
    {
        "name": "db_errors",
        "description": "Database error spike",
        "query": 'sum by(component) (count_over_time({component="postgresql", pg_level="ERROR"}[5m]))',
        "threshold": 10,
        "severity": "critical",
    },
    {
        "name": "oom_events",
        "description": "Out-of-memory events",
        "query": 'count_over_time({level="CRITICAL"} |= "OutOfMemory" [10m])',
        "threshold": 1,
        "severity": "critical",
    },
    {
        "name": "timeout_spike",
        "description": "Timeout error spike",
        "query": 'sum by(component) (count_over_time({level="ERROR"} |= "timeout" [5m]))',
        "threshold": 15,
        "severity": "warning",
    },
    {
        "name": "rate_limit_hits",
        "description": "Rate limiting events",
        "query": 'sum by(component) (count_over_time({level=~"WARN|ERROR"} |= "rate limit" [5m]))',
        "threshold": 50,
        "severity": "warning",
    },
]

_alert_cooldown: dict[str, float] = {}


async def query_loki(query: str) -> list[dict]:
    """Execute a LogQL query against Loki."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{LOKI_URL}/loki/api/v1/query",
                params={"query": query, "time": str(int(time.time()))},
            )
            data = resp.json()
            if data.get("status") == "success":
                return data.get("data", {}).get("result", [])
        except Exception as e:
            logger.warning(f"Loki query failed: {e}")
    return []


async def send_alert(pattern: dict, component: str, value: float):
    """Send pattern detection alert to Mattermost."""
    key = f"{pattern['name']}_{component}"
    now = time.time()
    if now - _alert_cooldown.get(key, 0) < 900:
        return
    _alert_cooldown[key] = now

    if MATTERMOST_WEBHOOK:
        icon = "🔴" if pattern["severity"] == "critical" else "🟡"
        payload = {
            "username": "Log Pattern Detector",
            "icon_emoji": ":mag:",
            "text": (
                f"### {icon} Log Pattern: {pattern['description']}\n"
                f"| Field | Value |\n|---|---|\n"
                f"| Pattern | `{pattern['name']}` |\n"
                f"| Component | `{component}` |\n"
                f"| Count (5m) | **{int(value)}** (threshold: {pattern['threshold']}) |\n"
                f"| Severity | {pattern['severity']} |\n"
                f"| Query | `{pattern['query'][:80]}...` |\n"
            ),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(MATTERMOST_WEBHOOK, json=payload)
            except Exception as e:
                logger.error(f"Alert failed: {e}")


async def run_detection():
    """Run all pattern detection queries."""
    for pattern in DETECTION_QUERIES:
        results = await query_loki(pattern["query"])
        for result in results:
            component = result.get("metric", {}).get("component", "unknown")
            value = float(result.get("value", [0, 0])[1])

            if pattern["name"] == "error_burst":
                error_rate_gauge.labels(component=component).set(value / 5)

            if value >= pattern["threshold"]:
                patterns_detected.labels(
                    pattern_type=pattern["name"], component=component
                ).inc()
                await send_alert(pattern, component, value)
                logger.warning(
                    f"Pattern detected: {pattern['name']} on {component} — "
                    f"count={int(value)} threshold={pattern['threshold']}"
                )


@app.on_event("startup")
async def startup():
    async def loop():
        while True:
            try:
                await run_detection()
            except Exception as e:
                logger.error(f"Detection error: {e}")
            await asyncio.sleep(CHECK_INTERVAL)
    asyncio.create_task(loop())


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/patterns")
async def get_patterns():
    return {"queries": [q["name"] for q in DETECTION_QUERIES], "cooldowns": len(_alert_cooldown)}
