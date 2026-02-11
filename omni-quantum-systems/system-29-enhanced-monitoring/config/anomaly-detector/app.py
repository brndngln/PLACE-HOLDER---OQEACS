"""
Omni Quantum Elite — Anomaly Detector Service
Analyzes Prometheus metrics using statistical methods (Z-score, IQR, EWMA)
to detect anomalies and alert via Mattermost + Omi wearable.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("anomaly-detector")

app = FastAPI(title="Omni Quantum Anomaly Detector", version="1.0.0")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://omni-prometheus:9090")
THANOS_URL = os.getenv("THANOS_URL", "http://omni-thanos-query:9091")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK", "")
OMI_WEBHOOK = os.getenv("OMI_WEBHOOK_URL", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
SENSITIVITY = float(os.getenv("ANOMALY_SENSITIVITY", "2.5"))

# ---------------------------------------------------------------------------
# Prometheus Metrics (self-instrumentation)
# ---------------------------------------------------------------------------
anomalies_detected = Counter("anomaly_detector_anomalies_total", "Total anomalies detected", ["metric", "severity"])
checks_performed = Counter("anomaly_detector_checks_total", "Total checks performed")
check_duration = Histogram("anomaly_detector_check_duration_seconds", "Check duration")
active_anomalies = Gauge("anomaly_detector_active_anomalies", "Currently active anomalies")

# ---------------------------------------------------------------------------
# Metric definitions to monitor for anomalies
# ---------------------------------------------------------------------------
MONITORED_METRICS = [
    {
        "name": "cpu_usage",
        "query": '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
        "description": "Host CPU usage %",
        "unit": "%",
        "window": "1h",
        "step": "60s",
    },
    {
        "name": "memory_usage",
        "query": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
        "description": "Host memory usage %",
        "unit": "%",
        "window": "1h",
        "step": "60s",
    },
    {
        "name": "litellm_latency_p95",
        "query": "histogram_quantile(0.95, rate(litellm_request_duration_seconds_bucket[5m]))",
        "description": "LiteLLM P95 latency",
        "unit": "s",
        "window": "2h",
        "step": "60s",
    },
    {
        "name": "litellm_error_rate",
        "query": "rate(litellm_request_errors_total[5m]) / rate(litellm_requests_total[5m])",
        "description": "LiteLLM error rate",
        "unit": "%",
        "window": "2h",
        "step": "60s",
    },
    {
        "name": "http_5xx_rate",
        "query": 'sum(rate(traefik_service_requests_total{code=~"5.."}[5m]))',
        "description": "Total 5xx error rate",
        "unit": "req/s",
        "window": "1h",
        "step": "60s",
    },
    {
        "name": "postgres_active_connections",
        "query": "pg_stat_activity_count",
        "description": "PostgreSQL active connections",
        "unit": "connections",
        "window": "2h",
        "step": "60s",
    },
    {
        "name": "redis_memory_usage",
        "query": "redis_memory_used_bytes / redis_memory_max_bytes * 100",
        "description": "Redis memory usage %",
        "unit": "%",
        "window": "1h",
        "step": "60s",
    },
    {
        "name": "disk_io_utilization",
        "query": "rate(node_disk_io_time_seconds_total[5m]) * 100",
        "description": "Disk I/O utilization %",
        "unit": "%",
        "window": "1h",
        "step": "60s",
    },
]

# In-memory state
_anomaly_state: dict[str, Any] = {}
_running = False


# ---------------------------------------------------------------------------
# Prometheus query helpers
# ---------------------------------------------------------------------------
async def query_prometheus(query: str) -> float | None:
    """Execute an instant query against Prometheus."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
            )
            data = resp.json()
            if data["status"] == "success" and data["data"]["result"]:
                return float(data["data"]["result"][0]["value"][1])
        except Exception as e:
            logger.warning(f"Prometheus query failed: {e}")
    return None


async def query_range(query: str, window: str, step: str) -> list[float]:
    """Execute a range query and return the values as a list of floats."""
    end = int(time.time())
    duration_map = {"1h": 3600, "2h": 7200, "6h": 21600, "24h": 86400}
    start = end - duration_map.get(window, 3600)

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query_range",
                params={"query": query, "start": start, "end": end, "step": step},
            )
            data = resp.json()
            if data["status"] == "success" and data["data"]["result"]:
                return [float(v[1]) for v in data["data"]["result"][0]["values"] if v[1] != "NaN"]
        except Exception as e:
            logger.warning(f"Prometheus range query failed: {e}")
    return []


# ---------------------------------------------------------------------------
# Anomaly detection algorithms
# ---------------------------------------------------------------------------
def detect_zscore(values: list[float], sensitivity: float) -> dict | None:
    """Z-score based anomaly detection on the most recent value."""
    if len(values) < 10:
        return None
    current = values[-1]
    historical = np.array(values[:-1])
    mean = np.mean(historical)
    std = np.std(historical)
    if std == 0:
        return None
    z = abs((current - mean) / std)
    if z > sensitivity:
        return {
            "method": "z-score",
            "z_score": round(z, 2),
            "current": round(current, 4),
            "mean": round(mean, 4),
            "std": round(std, 4),
            "direction": "above" if current > mean else "below",
        }
    return None


def detect_iqr(values: list[float]) -> dict | None:
    """IQR-based outlier detection."""
    if len(values) < 20:
        return None
    current = values[-1]
    arr = np.array(values[:-1])
    q1 = np.percentile(arr, 25)
    q3 = np.percentile(arr, 75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    if current < lower or current > upper:
        return {
            "method": "iqr",
            "current": round(current, 4),
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
            "bounds": [round(lower, 4), round(upper, 4)],
            "direction": "above" if current > upper else "below",
        }
    return None


def detect_ewma(values: list[float], span: int = 20, sensitivity: float = 2.5) -> dict | None:
    """Exponentially Weighted Moving Average anomaly detection."""
    if len(values) < span:
        return None
    current = values[-1]
    arr = np.array(values[:-1])
    alpha = 2.0 / (span + 1)
    ewma = arr[0]
    ewma_var = 0.0
    for v in arr[1:]:
        diff = v - ewma
        ewma = alpha * v + (1 - alpha) * ewma
        ewma_var = (1 - alpha) * (ewma_var + alpha * diff * diff)
    ewma_std = np.sqrt(ewma_var)
    if ewma_std == 0:
        return None
    deviation = abs(current - ewma) / ewma_std
    if deviation > sensitivity:
        return {
            "method": "ewma",
            "deviation": round(deviation, 2),
            "current": round(current, 4),
            "ewma": round(ewma, 4),
            "ewma_std": round(ewma_std, 4),
            "direction": "above" if current > ewma else "below",
        }
    return None


# ---------------------------------------------------------------------------
# Alerting
# ---------------------------------------------------------------------------
async def send_mattermost_alert(metric_name: str, description: str, anomaly: dict, severity: str):
    """Send anomaly alert to Mattermost #alerts channel."""
    if not MATTERMOST_WEBHOOK:
        return
    icon = "🔴" if severity == "critical" else "🟡"
    payload = {
        "username": "Anomaly Detector",
        "icon_emoji": ":chart_with_upwards_trend:",
        "text": (
            f"### {icon} Anomaly Detected: {description}\n"
            f"| Field | Value |\n|---|---|\n"
            f"| Metric | `{metric_name}` |\n"
            f"| Method | {anomaly['method']} |\n"
            f"| Current Value | `{anomaly['current']}` |\n"
            f"| Direction | {anomaly['direction']} |\n"
            f"| Severity | **{severity}** |\n"
            f"| Detected At | {datetime.now(timezone.utc).isoformat()} |\n"
        ),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(MATTERMOST_WEBHOOK, json=payload)
        except Exception as e:
            logger.error(f"Mattermost alert failed: {e}")


async def send_omi_alert(metric_name: str, description: str, severity: str):
    """Send anomaly alert to Omi wearable."""
    if not OMI_WEBHOOK:
        return
    payload = {
        "type": "anomaly",
        "severity": severity,
        "title": f"Anomaly: {description}",
        "metric": metric_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(OMI_WEBHOOK, json=payload)
        except Exception as e:
            logger.error(f"Omi alert failed: {e}")


# ---------------------------------------------------------------------------
# Main detection loop
# ---------------------------------------------------------------------------
async def run_detection_cycle():
    """Run one full cycle of anomaly detection across all monitored metrics."""
    active_count = 0
    for metric in MONITORED_METRICS:
        with check_duration.time():
            checks_performed.inc()
            values = await query_range(metric["query"], metric["window"], metric["step"])
            if not values:
                continue

            # Run all three detection methods
            anomaly = None
            severity = "warning"

            z_result = detect_zscore(values, SENSITIVITY)
            iqr_result = detect_iqr(values)
            ewma_result = detect_ewma(values, sensitivity=SENSITIVITY)

            # If multiple methods agree, raise severity
            detections = [r for r in [z_result, iqr_result, ewma_result] if r]
            if len(detections) >= 2:
                severity = "critical"
                anomaly = detections[0]
                anomaly["confirmed_by"] = [d["method"] for d in detections]
            elif len(detections) == 1:
                anomaly = detections[0]

            if anomaly:
                active_count += 1
                anomalies_detected.labels(metric=metric["name"], severity=severity).inc()
                key = metric["name"]
                # Deduplicate: don't re-alert within 15 minutes
                last_alert = _anomaly_state.get(key, 0)
                if time.time() - last_alert > 900:
                    _anomaly_state[key] = time.time()
                    await send_mattermost_alert(metric["name"], metric["description"], anomaly, severity)
                    if severity == "critical":
                        await send_omi_alert(metric["name"], metric["description"], severity)
                    logger.warning(f"Anomaly [{severity}] {metric['name']}: {anomaly}")
            else:
                # Clear state if metric returns to normal
                _anomaly_state.pop(metric["name"], None)

    active_anomalies.set(active_count)


async def detection_loop():
    """Continuous detection loop."""
    global _running
    _running = True
    logger.info(f"Anomaly detection started — interval={CHECK_INTERVAL}s, sensitivity={SENSITIVITY}")
    while _running:
        try:
            await run_detection_cycle()
        except Exception as e:
            logger.error(f"Detection cycle error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    asyncio.create_task(detection_loop())


@app.get("/health")
async def health():
    return {"status": "healthy", "running": _running, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/anomalies")
async def get_anomalies():
    return {
        "active_anomalies": len(_anomaly_state),
        "alerts": {k: datetime.fromtimestamp(v, tz=timezone.utc).isoformat() for k, v in _anomaly_state.items()},
    }


@app.post("/check")
async def trigger_check():
    await run_detection_cycle()
    return {"status": "check_complete", "active_anomalies": len(_anomaly_state)}


@app.get("/config")
async def get_config():
    return {
        "check_interval": CHECK_INTERVAL,
        "sensitivity": SENSITIVITY,
        "monitored_metrics": [m["name"] for m in MONITORED_METRICS],
    }
