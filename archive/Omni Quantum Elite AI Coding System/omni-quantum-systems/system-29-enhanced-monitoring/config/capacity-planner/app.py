"""
Omni Quantum Elite — Capacity Planner Service
Forecasts resource usage using linear regression and exponential smoothing.
Alerts when projected usage exceeds thresholds.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import httpx
import numpy as np
from fastapi import FastAPI
from prometheus_client import Gauge, generate_latest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("capacity-planner")

app = FastAPI(title="Omni Quantum Capacity Planner", version="1.0.0")

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://omni-prometheus:9090")
THANOS_URL = os.getenv("THANOS_URL", "http://omni-thanos-query:9091")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK", "")
FORECAST_DAYS = int(os.getenv("FORECAST_HORIZON_DAYS", "30"))

# Metrics
forecast_value = Gauge("capacity_forecast_value", "Forecasted value", ["resource", "horizon_days"])
forecast_days_to_threshold = Gauge("capacity_days_to_threshold", "Days until threshold", ["resource"])

RESOURCES = [
    {
        "name": "disk_usage_percent",
        "query": '(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100',
        "threshold": 90,
        "unit": "%",
        "description": "Root disk usage",
    },
    {
        "name": "memory_usage_percent",
        "query": "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100",
        "threshold": 90,
        "unit": "%",
        "description": "Memory usage",
    },
    {
        "name": "cpu_usage_percent",
        "query": '100 - avg(rate(node_cpu_seconds_total{mode="idle"}[1h])) * 100',
        "threshold": 85,
        "unit": "%",
        "description": "CPU usage",
    },
    {
        "name": "postgres_connections_percent",
        "query": "pg_stat_activity_count / pg_settings_max_connections * 100",
        "threshold": 80,
        "unit": "%",
        "description": "PostgreSQL connection utilization",
    },
    {
        "name": "redis_memory_percent",
        "query": "redis_memory_used_bytes / redis_memory_max_bytes * 100",
        "threshold": 85,
        "unit": "%",
        "description": "Redis memory utilization",
    },
]


async def query_range_7d(query: str) -> list[tuple[float, float]]:
    """Query 7 days of data with 1h resolution for trend analysis."""
    end = int(time.time())
    start = end - 7 * 86400
    url = THANOS_URL or PROMETHEUS_URL
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"{url}/api/v1/query_range",
                params={"query": query, "start": start, "end": end, "step": "3600"},
            )
            data = resp.json()
            if data["status"] == "success" and data["data"]["result"]:
                return [(float(v[0]), float(v[1])) for v in data["data"]["result"][0]["values"] if v[1] != "NaN"]
        except Exception as e:
            logger.warning(f"Range query failed: {e}")
    return []


def linear_forecast(data_points: list[tuple[float, float]], horizon_days: int) -> dict:
    """Simple linear regression forecast."""
    if len(data_points) < 24:
        return {"error": "insufficient data"}
    timestamps = np.array([p[0] for p in data_points])
    values = np.array([p[1] for p in data_points])
    # Normalize timestamps to days
    t_days = (timestamps - timestamps[0]) / 86400
    # Linear fit
    coeffs = np.polyfit(t_days, values, 1)
    slope_per_day = coeffs[0]
    current = values[-1]
    forecast_values = {}
    for d in [7, 14, 30]:
        if d <= horizon_days:
            forecast_values[f"{d}d"] = round(current + slope_per_day * d, 2)
    return {
        "current": round(current, 2),
        "slope_per_day": round(slope_per_day, 4),
        "trend": "increasing" if slope_per_day > 0.01 else "decreasing" if slope_per_day < -0.01 else "stable",
        "forecasts": forecast_values,
    }


def days_to_threshold(current: float, slope_per_day: float, threshold: float) -> float | None:
    """Calculate days until threshold is reached."""
    if slope_per_day <= 0:
        return None  # Decreasing or flat — won't reach threshold
    remaining = threshold - current
    if remaining <= 0:
        return 0  # Already exceeded
    return round(remaining / slope_per_day, 1)


async def run_forecast_cycle():
    """Run forecasts for all resources."""
    results = {}
    for resource in RESOURCES:
        data = await query_range_7d(resource["query"])
        if not data:
            continue
        forecast = linear_forecast(data, FORECAST_DAYS)
        if "error" in forecast:
            continue
        # Set Prometheus metrics
        for horizon, value in forecast.get("forecasts", {}).items():
            days = int(horizon.replace("d", ""))
            forecast_value.labels(resource=resource["name"], horizon_days=str(days)).set(value)
        # Days to threshold
        dtt = days_to_threshold(forecast["current"], forecast["slope_per_day"], resource["threshold"])
        if dtt is not None:
            forecast_days_to_threshold.labels(resource=resource["name"]).set(dtt)
            if dtt < 7:
                await alert_capacity(resource, forecast, dtt)
        results[resource["name"]] = {**forecast, "threshold": resource["threshold"], "days_to_threshold": dtt}
    return results


async def alert_capacity(resource: dict, forecast: dict, days: float):
    """Alert when capacity threshold approaching."""
    if not MATTERMOST_WEBHOOK:
        return
    payload = {
        "username": "Capacity Planner",
        "icon_emoji": ":chart_with_upwards_trend:",
        "text": (
            f"### ⚠️ Capacity Warning: {resource['description']}\n"
            f"| Field | Value |\n|---|---|\n"
            f"| Resource | `{resource['name']}` |\n"
            f"| Current | {forecast['current']}{resource['unit']} |\n"
            f"| Threshold | {resource['threshold']}{resource['unit']} |\n"
            f"| Days Until Threshold | **{days}** |\n"
            f"| Trend | {forecast['trend']} ({forecast['slope_per_day']}/day) |\n"
        ),
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(MATTERMOST_WEBHOOK, json=payload)
        except Exception as e:
            logger.error(f"Alert failed: {e}")


@app.on_event("startup")
async def startup():
    async def loop():
        while True:
            try:
                await run_forecast_cycle()
            except Exception as e:
                logger.error(f"Forecast cycle error: {e}")
            await asyncio.sleep(3600)  # Run hourly
    asyncio.create_task(loop())


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/forecast")
async def get_forecast():
    return await run_forecast_cycle()
