#!/usr/bin/env python3
"""
SYSTEM 13 — AI OBSERVABILITY: Trace Correlation Service
Omni Quantum Elite AI Coding System — Observability Layer

FastAPI service (port 3001) that links Langfuse traces to Loki logs,
providing unified timelines for end-to-end AI pipeline observability.

Includes Prometheus metrics at /metrics for request count and latency histogram.
Loads Langfuse credentials from Vault at startup.

Requirements: fastapi, uvicorn, httpx, hvac, structlog, prometheus-client
"""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import httpx
import hvac
import structlog
from fastapi import FastAPI, HTTPException, Query, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Structured Logging
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger(
    service="trace-correlator", system="13", component="ai-observability"
)

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------

REQUEST_COUNT = Counter(
    "correlator_requests_total",
    "Total HTTP requests to the trace correlator",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "correlator_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LANGFUSE_URL = os.getenv("LANGFUSE_URL", "http://omni-langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LOKI_URL = os.getenv("LOKI_URL", "http://omni-loki:3100")
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://omni-vault:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")
VAULT_LANGFUSE_PATH = os.getenv(
    "VAULT_LANGFUSE_PATH", "langfuse/projects/omni-pipeline"
)


def load_langfuse_credentials_from_vault() -> tuple[str, str]:
    """Load Langfuse public/secret keys from Vault KV v2.

    Falls back to environment variables if Vault is unavailable.

    Returns:
        Tuple of (public_key, secret_key).
    """
    if not VAULT_TOKEN:
        log.info(
            "vault_token_not_set",
            fallback="environment variables",
        )
        return LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

    try:
        vault_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
        if not vault_client.is_authenticated():
            log.warning("vault_auth_failed", fallback="environment variables")
            return LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

        secret = vault_client.secrets.kv.v2.read_secret_version(
            path=VAULT_LANGFUSE_PATH,
            mount_point="secret",
        )
        data = secret.get("data", {}).get("data", {})
        pub = data.get("public_key", "")
        sec = data.get("secret_key", "")

        if pub and sec:
            log.info(
                "vault_credentials_loaded",
                path=f"secret/data/{VAULT_LANGFUSE_PATH}",
            )
            return pub, sec

        log.warning(
            "vault_credentials_empty",
            path=VAULT_LANGFUSE_PATH,
            fallback="environment variables",
        )
    except Exception as exc:
        log.warning(
            "vault_read_failed",
            error=str(exc),
            fallback="environment variables",
        )

    return LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY


# Resolved credentials (populated at startup)
_langfuse_public_key: str = ""
_langfuse_secret_key: str = ""

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    """Type of event in a unified timeline."""

    LLM_CALL = "llm_call"
    SPAN = "span"
    LOG = "log"
    GENERATION = "generation"
    SCORE = "score"


class TimelineEvent(BaseModel):
    """A single event in the unified timeline."""

    timestamp: datetime
    event_type: EventType
    source: str = Field(description="'langfuse' or 'loki'")
    container: str | None = None
    level: str | None = None
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class UnifiedTimeline(BaseModel):
    """Merged timeline of Langfuse trace + Loki logs."""

    trace_id: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: float | None = None
    total_events: int = 0
    langfuse_events: int = 0
    loki_events: int = 0
    events: list[TimelineEvent] = Field(default_factory=list)
    trace_metadata: dict[str, Any] = Field(default_factory=dict)


class TraceCost(BaseModel):
    """Cost breakdown for a single trace."""

    trace_id: str
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0
    models_used: list[str] = Field(default_factory=list)
    cost_breakdown: list[dict[str, Any]] = Field(default_factory=list)


class ExpensiveTrace(BaseModel):
    """Summary of an expensive trace."""

    trace_id: str
    name: str | None = None
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    duration_ms: float | None = None
    model: str | None = None
    timestamp: datetime | None = None
    status: str | None = None


class HealthResponse(BaseModel):
    """Service health status."""

    status: str
    langfuse_connected: bool
    loki_connected: bool


# ---------------------------------------------------------------------------
# Application Lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load credentials from Vault on startup."""
    global _langfuse_public_key, _langfuse_secret_key
    log.info("starting_trace_correlator", port=3001)
    _langfuse_public_key, _langfuse_secret_key = (
        load_langfuse_credentials_from_vault()
    )
    yield
    log.info("shutting_down_trace_correlator")


app = FastAPI(
    title="Omni Quantum Trace Correlator",
    description=(
        "Links Langfuse AI traces to Loki application logs "
        "for unified observability"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware: Prometheus instrumentation
# ---------------------------------------------------------------------------


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next) -> Response:
    """Record request count and latency for Prometheus."""
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    path = request.url.path
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start

    REQUEST_COUNT.labels(
        method=method, endpoint=path, status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

    return response


# ---------------------------------------------------------------------------
# Langfuse Client
# ---------------------------------------------------------------------------


async def fetch_langfuse_trace(trace_id: str) -> dict[str, Any]:
    """Fetch trace details from Langfuse API."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{LANGFUSE_URL}/api/public/traces/{trace_id}",
            auth=(_langfuse_public_key, _langfuse_secret_key),
        )
        if resp.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Trace {trace_id} not found in Langfuse",
            )
        if resp.status_code != 200:
            log.error(
                "langfuse_trace_fetch_failed",
                trace_id=trace_id,
                status=resp.status_code,
            )
            raise HTTPException(
                status_code=502,
                detail=f"Langfuse returned {resp.status_code}: {resp.text}",
            )
        return resp.json()


async def fetch_langfuse_observations(
    trace_id: str,
) -> list[dict[str, Any]]:
    """Fetch all observations (generations, spans) for a trace."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{LANGFUSE_URL}/api/public/observations",
            params={"traceId": trace_id, "limit": 1000},
            auth=(_langfuse_public_key, _langfuse_secret_key),
        )
        if resp.status_code != 200:
            log.warning(
                "langfuse_observations_failed",
                trace_id=trace_id,
                status=resp.status_code,
            )
            return []
        data = resp.json()
        return data.get("data", [])


async def fetch_langfuse_scores(trace_id: str) -> list[dict[str, Any]]:
    """Fetch scores associated with a trace."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{LANGFUSE_URL}/api/public/scores",
            params={"traceId": trace_id, "limit": 100},
            auth=(_langfuse_public_key, _langfuse_secret_key),
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("data", [])


async def fetch_langfuse_traces(
    limit: int = 10,
    order_by: str = "totalCost",
    from_timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch traces from Langfuse, ordered by cost."""
    params: dict[str, Any] = {"limit": limit, "orderBy": order_by}
    if from_timestamp:
        params["fromTimestamp"] = from_timestamp

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{LANGFUSE_URL}/api/public/traces",
            params=params,
            auth=(_langfuse_public_key, _langfuse_secret_key),
        )
        if resp.status_code != 200:
            log.warning(
                "langfuse_traces_fetch_failed", status=resp.status_code
            )
            return []
        data = resp.json()
        return data.get("data", [])


# ---------------------------------------------------------------------------
# Loki Client
# ---------------------------------------------------------------------------


async def fetch_loki_logs(
    trace_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Query Loki for log entries matching a trace_id."""
    if start is None:
        start = datetime.now(timezone.utc) - timedelta(hours=24)
    if end is None:
        end = datetime.now(timezone.utc)

    start_ns = str(int(start.timestamp() * 1e9))
    end_ns = str(int(end.timestamp() * 1e9))

    query = f'{{omni_tier=~".+"}} | json | trace_id = `{trace_id}`'

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params={
                "query": query,
                "start": start_ns,
                "end": end_ns,
                "limit": 5000,
                "direction": "forward",
            },
        )
        if resp.status_code != 200:
            log.warning(
                "loki_query_failed",
                trace_id=trace_id,
                status=resp.status_code,
            )
            return []

        data = resp.json()
        results = data.get("data", {}).get("result", [])

        log_entries: list[dict[str, Any]] = []
        for stream in results:
            labels = stream.get("stream", {})
            for ts_ns, line in stream.get("values", []):
                log_entries.append(
                    {
                        "timestamp": datetime.fromtimestamp(
                            int(ts_ns) / 1e9, tz=timezone.utc
                        ),
                        "container": labels.get("container", ""),
                        "level": labels.get("level", ""),
                        "message": line,
                        "labels": labels,
                    }
                )
        return log_entries


# ---------------------------------------------------------------------------
# Timeline Builder
# ---------------------------------------------------------------------------


def parse_iso_timestamp(ts_str: str | None) -> datetime | None:
    """Parse ISO timestamp string to datetime."""
    if not ts_str:
        return None
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def build_langfuse_events(
    trace: dict[str, Any],
    observations: list[dict[str, Any]],
    scores: list[dict[str, Any]],
) -> list[TimelineEvent]:
    """Convert Langfuse trace data into timeline events."""
    events: list[TimelineEvent] = []

    for obs in observations:
        ts = parse_iso_timestamp(obs.get("startTime"))
        if not ts:
            continue

        obs_type = obs.get("type", "").lower()
        if obs_type == "generation":
            event_type = EventType.GENERATION
        elif obs_type == "span":
            event_type = EventType.SPAN
        else:
            event_type = EventType.LLM_CALL

        usage = obs.get("usage", {}) or {}
        model = obs.get("model", "")
        cost = obs.get("calculatedTotalCost")

        metadata: dict[str, Any] = {
            "observation_id": obs.get("id", ""),
            "model": model,
            "input_tokens": usage.get("input", 0)
            or usage.get("promptTokens", 0),
            "output_tokens": usage.get("output", 0)
            or usage.get("completionTokens", 0),
            "total_tokens": usage.get("total", 0)
            or usage.get("totalTokens", 0),
            "cost_usd": float(cost) if cost else 0.0,
            "status": obs.get("statusMessage", obs.get("level", "")),
        }

        end_ts = parse_iso_timestamp(obs.get("endTime"))
        if end_ts and ts:
            metadata["duration_ms"] = (end_ts - ts).total_seconds() * 1000

        events.append(
            TimelineEvent(
                timestamp=ts,
                event_type=event_type,
                source="langfuse",
                message=obs.get("name", f"{obs_type} observation"),
                metadata=metadata,
            )
        )

    for score in scores:
        ts = parse_iso_timestamp(score.get("timestamp"))
        if not ts:
            continue
        events.append(
            TimelineEvent(
                timestamp=ts,
                event_type=EventType.SCORE,
                source="langfuse",
                message=f"Score: {score.get('name', 'unnamed')} = {score.get('value', 'N/A')}",
                metadata={
                    "score_name": score.get("name", ""),
                    "score_value": score.get("value"),
                    "comment": score.get("comment", ""),
                },
            )
        )

    return events


def build_loki_events(log_entries: list[dict[str, Any]]) -> list[TimelineEvent]:
    """Convert Loki log entries into timeline events."""
    events: list[TimelineEvent] = []
    for entry in log_entries:
        events.append(
            TimelineEvent(
                timestamp=entry["timestamp"],
                event_type=EventType.LOG,
                source="loki",
                container=entry.get("container", ""),
                level=entry.get("level", ""),
                message=entry.get("message", ""),
                metadata={"labels": entry.get("labels", {})},
            )
        )
    return events


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.get("/metrics")
async def prometheus_metrics() -> Response:
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check connectivity to Langfuse and Loki."""
    langfuse_ok = False
    loki_ok = False

    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.get(f"{LANGFUSE_URL}/api/public/health")
            langfuse_ok = resp.status_code == 200
        except Exception:
            pass

        try:
            resp = await client.get(f"{LOKI_URL}/ready")
            loki_ok = resp.status_code == 200
        except Exception:
            pass

    status = "healthy" if (langfuse_ok and loki_ok) else "degraded"
    return HealthResponse(
        status=status,
        langfuse_connected=langfuse_ok,
        loki_connected=loki_ok,
    )


@app.get("/trace/{trace_id}/unified", response_model=UnifiedTimeline)
async def get_unified_timeline(trace_id: str) -> UnifiedTimeline:
    """Get merged timeline of Langfuse trace + Loki logs for a trace ID.

    Returns LLM calls, spans, scores, and application logs interleaved
    chronologically for complete end-to-end request tracing.
    """
    log.info("unified_timeline_request", trace_id=trace_id)

    trace = await fetch_langfuse_trace(trace_id)
    observations = await fetch_langfuse_observations(trace_id)
    scores = await fetch_langfuse_scores(trace_id)

    trace_start = parse_iso_timestamp(trace.get("timestamp"))
    trace_end = parse_iso_timestamp(trace.get("updatedAt"))
    loki_start = (trace_start - timedelta(minutes=5)) if trace_start else None
    loki_end = (trace_end + timedelta(minutes=5)) if trace_end else None

    log_entries = await fetch_loki_logs(
        trace_id, start=loki_start, end=loki_end
    )

    langfuse_events = build_langfuse_events(trace, observations, scores)
    loki_events = build_loki_events(log_entries)

    all_events = langfuse_events + loki_events
    all_events.sort(key=lambda e: e.timestamp)

    start_time = all_events[0].timestamp if all_events else trace_start
    end_time = all_events[-1].timestamp if all_events else trace_end
    duration_ms = None
    if start_time and end_time:
        duration_ms = (end_time - start_time).total_seconds() * 1000

    trace_metadata = {
        "name": trace.get("name", ""),
        "status": trace.get("status", ""),
        "user_id": trace.get("userId", ""),
        "session_id": trace.get("sessionId", ""),
        "tags": trace.get("tags", []),
        "input": trace.get("input"),
        "output": trace.get("output"),
        "total_cost": trace.get("totalCost"),
    }

    log.info(
        "unified_timeline_built",
        trace_id=trace_id,
        langfuse_events=len(langfuse_events),
        loki_events=len(loki_events),
    )

    return UnifiedTimeline(
        trace_id=trace_id,
        start_time=start_time,
        end_time=end_time,
        duration_ms=duration_ms,
        total_events=len(all_events),
        langfuse_events=len(langfuse_events),
        loki_events=len(loki_events),
        events=all_events,
        trace_metadata=trace_metadata,
    )


@app.get("/trace/{trace_id}/cost", response_model=TraceCost)
async def get_trace_cost(trace_id: str) -> TraceCost:
    """Get total cost breakdown for a trace across all LLM calls."""
    log.info("cost_request", trace_id=trace_id)
    observations = await fetch_langfuse_observations(trace_id)

    total_cost = 0.0
    total_input = 0
    total_output = 0
    total_tokens = 0
    models_used: set[str] = set()
    cost_breakdown: list[dict[str, Any]] = []
    llm_calls = 0

    for obs in observations:
        if obs.get("type", "").lower() not in ("generation", "llm"):
            continue

        llm_calls += 1
        usage = obs.get("usage", {}) or {}
        cost = obs.get("calculatedTotalCost")
        model = obs.get("model", "unknown")

        input_tokens = (
            usage.get("input", 0) or usage.get("promptTokens", 0) or 0
        )
        output_tokens = (
            usage.get("output", 0) or usage.get("completionTokens", 0) or 0
        )
        obs_total = (
            usage.get("total", 0) or usage.get("totalTokens", 0) or 0
        )
        obs_cost = float(cost) if cost else 0.0

        total_cost += obs_cost
        total_input += input_tokens
        total_output += output_tokens
        total_tokens += obs_total
        if model:
            models_used.add(model)

        cost_breakdown.append(
            {
                "observation_id": obs.get("id", ""),
                "name": obs.get("name", ""),
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": obs_total,
                "cost_usd": obs_cost,
                "timestamp": obs.get("startTime", ""),
            }
        )

    return TraceCost(
        trace_id=trace_id,
        total_cost_usd=round(total_cost, 6),
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total_tokens,
        llm_calls=llm_calls,
        models_used=sorted(models_used),
        cost_breakdown=cost_breakdown,
    )


@app.get("/traces/expensive", response_model=list[ExpensiveTrace])
async def get_expensive_traces(
    top: int = Query(
        default=10, ge=1, le=100, description="Number of traces to return"
    ),
    hours: int = Query(
        default=24, ge=1, le=720, description="Lookback period in hours"
    ),
) -> list[ExpensiveTrace]:
    """Get the most expensive traces in the specified time period."""
    log.info("expensive_traces_request", top=top, hours=hours)
    from_ts = (
        datetime.now(timezone.utc) - timedelta(hours=hours)
    ).isoformat()

    traces = await fetch_langfuse_traces(
        limit=top,
        order_by="totalCost",
        from_timestamp=from_ts,
    )

    result: list[ExpensiveTrace] = []
    for t in traces:
        ts = parse_iso_timestamp(t.get("timestamp"))
        start = ts
        end = parse_iso_timestamp(t.get("updatedAt"))
        duration = None
        if start and end:
            duration = (end - start).total_seconds() * 1000

        obs_meta = t.get("observations", [])
        model = None
        if isinstance(obs_meta, list) and obs_meta:
            model = obs_meta[0].get("model")

        result.append(
            ExpensiveTrace(
                trace_id=t.get("id", ""),
                name=t.get("name"),
                total_cost_usd=float(t.get("totalCost", 0) or 0),
                total_tokens=int(t.get("totalTokens", 0) or 0),
                duration_ms=duration,
                model=model,
                timestamp=ts,
                status=t.get("status"),
            )
        )

    result.sort(key=lambda x: x.total_cost_usd, reverse=True)
    return result[:top]


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "correlator:app",
        host="0.0.0.0",
        port=3001,
        log_level="info",
        access_log=True,
    )
