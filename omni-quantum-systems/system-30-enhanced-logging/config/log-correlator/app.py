"""
Omni Quantum Elite — Log Correlator
Links Loki logs with Langfuse AI traces via trace_id correlation.
Provides unified view of AI request lifecycle: logs + traces + metrics.
"""

import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Query
from prometheus_client import Counter, generate_latest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("log-correlator")

app = FastAPI(title="Omni Quantum Log Correlator", version="1.0.0")

LOKI_URL = os.getenv("LOKI_URL", "http://omni-loki:3100")
LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")

correlations_performed = Counter("log_correlations_total", "Total correlations performed")


async def get_logs_by_trace(trace_id: str, limit: int = 100) -> list[dict]:
    """Fetch logs from Loki filtered by trace ID."""
    query = f'{{trace_id="{trace_id}"}}'
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={"query": query, "limit": limit},
            )
            data = resp.json()
            if data.get("status") == "success":
                logs = []
                for stream in data.get("data", {}).get("result", []):
                    labels = stream.get("stream", {})
                    for ts, line in stream.get("values", []):
                        logs.append({"timestamp": ts, "labels": labels, "line": line})
                return sorted(logs, key=lambda x: x["timestamp"])
        except Exception as e:
            logger.warning(f"Loki query failed: {e}")
    return []


async def get_langfuse_trace(trace_id: str) -> dict | None:
    """Fetch trace details from Langfuse."""
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{LANGFUSE_URL}/api/public/traces/{trace_id}",
                auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"Langfuse query failed: {e}")
    return None


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/correlate/{trace_id}")
async def correlate(trace_id: str, include_logs: bool = True, include_trace: bool = True):
    """Correlate logs and AI trace data for a given trace ID."""
    correlations_performed.inc()
    result = {"trace_id": trace_id, "timestamp": datetime.now(timezone.utc).isoformat()}

    if include_logs:
        result["logs"] = await get_logs_by_trace(trace_id)
        result["log_count"] = len(result["logs"])

    if include_trace:
        trace = await get_langfuse_trace(trace_id)
        if trace:
            result["trace"] = {
                "name": trace.get("name"),
                "status": trace.get("status"),
                "duration_ms": trace.get("latency"),
                "model": trace.get("model"),
                "tokens": trace.get("usage", {}),
                "cost": trace.get("calculatedTotalCost"),
                "metadata": trace.get("metadata"),
            }
            # Extract observations (spans)
            result["spans"] = [
                {
                    "name": obs.get("name"),
                    "type": obs.get("type"),
                    "duration_ms": obs.get("latency"),
                    "model": obs.get("model"),
                    "status": obs.get("status"),
                }
                for obs in trace.get("observations", [])
            ]

    return result


@app.get("/search")
async def search_logs(
    component: str = Query(None),
    level: str = Query(None),
    text: str = Query(None),
    limit: int = Query(50, le=500),
):
    """Search logs with filters."""
    label_parts = []
    if component:
        label_parts.append(f'component="{component}"')
    if level:
        label_parts.append(f'level="{level}"')
    labels = ", ".join(label_parts) if label_parts else ""

    query = f"{{{labels}}}"
    if text:
        query += f' |= "{text}"'

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={"query": query, "limit": limit},
            )
            data = resp.json()
            if data.get("status") == "success":
                logs = []
                for stream in data.get("data", {}).get("result", []):
                    for ts, line in stream.get("values", []):
                        logs.append({"timestamp": ts, "line": line, "labels": stream.get("stream", {})})
                return {"count": len(logs), "logs": logs}
        except Exception as e:
            return {"error": str(e)}
    return {"count": 0, "logs": []}
