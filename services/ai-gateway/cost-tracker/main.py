# ===========================================================================
# SYSTEM 3 -- AI GATEWAY: Cost Tracker Service
# Omni Quantum Elite AI Coding System -- AI Spend Monitoring
#
# FastAPI microservice (port 4001) that reads generation data from
# Langfuse, computes per-model and per-service costs, tracks budget
# utilisation, and posts daily summaries to Mattermost.
#
# Endpoints:
#   GET /costs/today          -- today's costs broken down by model
#   GET /costs/range          -- costs for an arbitrary date range
#   GET /costs/by-service     -- costs grouped by calling service
#   GET /budget/status        -- budget utilisation vs configured limits
#   GET /health               -- liveness probe
#   GET /ready                -- readiness probe
#   GET /metrics              -- Prometheus metrics
# ===========================================================================

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import httpx
import structlog
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# ──────────────────────────────────────────────────────────
# Structured logging
# ──────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if os.getenv("LOG_FORMAT") == "console" else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.get_config().get("min_level", 0)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("cost-tracker")

# ──────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://omni-langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
MATTERMOST_WEBHOOK_URL = os.getenv("MATTERMOST_WEBHOOK_URL", "")

# Monthly budget ceiling in USD
MONTHLY_BUDGET_USD = float(os.getenv("MONTHLY_BUDGET_USD", "500.0"))
DAILY_BUDGET_USD = float(os.getenv("DAILY_BUDGET_USD", "25.0"))

# ──────────────────────────────────────────────────────────
# Cost-per-token lookup (USD per 1 million tokens)
# Must stay in sync with middleware/request-logger.py
# ──────────────────────────────────────────────────────────
COST_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "ollama/devstral-2-123b": {"input": 0.60, "output": 1.80},
    "ollama/deepseek-v3.2": {"input": 0.30, "output": 0.90},
    "ollama/qwen3-coder-30b": {"input": 0.15, "output": 0.45},
    "ollama/kimi-dev-72b": {"input": 0.40, "output": 1.20},
}
DEFAULT_COST = {"input": 0.25, "output": 0.75}

# ──────────────────────────────────────────────────────────
# Prometheus metrics
# ──────────────────────────────────────────────────────────
registry = CollectorRegistry()

COST_TOTAL = Counter(
    "ai_gateway_cost_usd_total",
    "Cumulative estimated cost in USD",
    ["model", "service"],
    registry=registry,
)

COST_DAILY = Gauge(
    "ai_gateway_cost_usd_today",
    "Estimated cost in USD for today",
    ["model"],
    registry=registry,
)

BUDGET_UTILISATION = Gauge(
    "ai_gateway_budget_utilisation_pct",
    "Budget utilisation percentage",
    ["period"],
    registry=registry,
)

TOKENS_TOTAL = Counter(
    "ai_gateway_tokens_total",
    "Total tokens processed",
    ["model", "direction"],
    registry=registry,
)

REQUEST_LATENCY = Histogram(
    "cost_tracker_request_duration_seconds",
    "Latency of cost-tracker endpoint requests",
    ["endpoint"],
    registry=registry,
)

LANGFUSE_ERRORS = Counter(
    "cost_tracker_langfuse_errors_total",
    "Number of failed Langfuse API calls",
    registry=registry,
)

# ──────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────

def _calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Compute estimated USD cost from token counts."""
    rates = COST_PER_MILLION_TOKENS.get(model, DEFAULT_COST)
    input_cost = (prompt_tokens / 1_000_000) * rates["input"]
    output_cost = (completion_tokens / 1_000_000) * rates["output"]
    return round(input_cost + output_cost, 8)


def _start_of_day(d: date) -> str:
    """ISO timestamp for the start of a date in UTC."""
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).isoformat()


def _end_of_day(d: date) -> str:
    """ISO timestamp for the end of a date in UTC."""
    return datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc).isoformat()


def _start_of_month() -> str:
    """ISO timestamp for the 1st of the current month."""
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────
# Langfuse client
# ──────────────────────────────────────────────────────────

class LangfuseClient:
    """Thin async wrapper around the Langfuse public API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=LANGFUSE_HOST,
            auth=(LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY),
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_generations(
        self,
        start_time: str,
        end_time: str,
        page: int = 1,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Fetch a page of generation records from Langfuse."""
        params: dict[str, Any] = {
            "fromTimestamp": start_time,
            "toTimestamp": end_time,
            "page": page,
            "limit": limit,
        }
        try:
            response = await self._client.get("/api/public/generations", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            LANGFUSE_ERRORS.inc()
            logger.error(
                "langfuse_api_error",
                status=exc.response.status_code,
                body=exc.response.text[:500],
            )
            return {"data": [], "meta": {"totalItems": 0, "page": page, "totalPages": 0}}
        except httpx.HTTPError as exc:
            LANGFUSE_ERRORS.inc()
            logger.error("langfuse_network_error", error=str(exc))
            return {"data": [], "meta": {"totalItems": 0, "page": page, "totalPages": 0}}

    async def fetch_all_generations(self, start_time: str, end_time: str) -> list[dict]:
        """Paginate through all generations for a time window."""
        all_generations: list[dict] = []
        page = 1
        while True:
            result = await self.fetch_generations(start_time, end_time, page=page, limit=500)
            data = result.get("data", [])
            all_generations.extend(data)
            meta = result.get("meta", {})
            total_pages = meta.get("totalPages", 1)
            if page >= total_pages or not data:
                break
            page += 1
        return all_generations


# ──────────────────────────────────────────────────────────
# Cost aggregation logic
# ──────────────────────────────────────────────────────────

def _aggregate_by_model(generations: list[dict]) -> dict[str, dict[str, Any]]:
    """Group generations by model and compute cost totals."""
    model_costs: dict[str, dict[str, Any]] = {}
    for gen in generations:
        model = gen.get("model", "unknown")
        usage = gen.get("usage", {}) or {}
        prompt_tokens = usage.get("input", 0) or 0
        completion_tokens = usage.get("output", 0) or 0
        cost = _calc_cost(model, prompt_tokens, completion_tokens)

        if model not in model_costs:
            model_costs[model] = {
                "model": model,
                "total_cost_usd": 0.0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "request_count": 0,
            }
        model_costs[model]["total_cost_usd"] = round(model_costs[model]["total_cost_usd"] + cost, 8)
        model_costs[model]["total_prompt_tokens"] += prompt_tokens
        model_costs[model]["total_completion_tokens"] += completion_tokens
        model_costs[model]["request_count"] += 1

    return model_costs


def _aggregate_by_service(generations: list[dict]) -> dict[str, dict[str, Any]]:
    """Group generations by calling service and compute cost totals."""
    service_costs: dict[str, dict[str, Any]] = {}
    for gen in generations:
        model = gen.get("model", "unknown")
        metadata = gen.get("metadata", {}) or {}
        service = metadata.get("service", "unknown")
        usage = gen.get("usage", {}) or {}
        prompt_tokens = usage.get("input", 0) or 0
        completion_tokens = usage.get("output", 0) or 0
        cost = _calc_cost(model, prompt_tokens, completion_tokens)

        if service not in service_costs:
            service_costs[service] = {
                "service": service,
                "total_cost_usd": 0.0,
                "total_tokens": 0,
                "request_count": 0,
                "models_used": set(),
            }
        service_costs[service]["total_cost_usd"] = round(service_costs[service]["total_cost_usd"] + cost, 8)
        service_costs[service]["total_tokens"] += prompt_tokens + completion_tokens
        service_costs[service]["request_count"] += 1
        service_costs[service]["models_used"].add(model)

    # Convert sets to lists for JSON serialisation
    for entry in service_costs.values():
        entry["models_used"] = sorted(entry["models_used"])

    return service_costs


# ──────────────────────────────────────────────────────────
# Mattermost daily summary
# ──────────────────────────────────────────────────────────

async def _post_daily_summary(langfuse: LangfuseClient) -> None:
    """Compute yesterday's costs and POST a Markdown summary to Mattermost."""
    yesterday = date.today() - timedelta(days=1)
    start = _start_of_day(yesterday)
    end = _end_of_day(yesterday)

    logger.info("daily_summary_starting", date=str(yesterday))

    generations = await langfuse.fetch_all_generations(start, end)
    model_costs = _aggregate_by_model(generations)

    total_cost = sum(m["total_cost_usd"] for m in model_costs.values())
    total_requests = sum(m["request_count"] for m in model_costs.values())
    total_prompt = sum(m["total_prompt_tokens"] for m in model_costs.values())
    total_completion = sum(m["total_completion_tokens"] for m in model_costs.values())

    # Build the Mattermost message
    lines = [
        f"### :bar_chart: AI Gateway Daily Cost Report -- {yesterday.isoformat()}",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| **Total Cost** | ${total_cost:.4f} |",
        f"| **Total Requests** | {total_requests:,} |",
        f"| **Prompt Tokens** | {total_prompt:,} |",
        f"| **Completion Tokens** | {total_completion:,} |",
        f"| **Daily Budget** | ${DAILY_BUDGET_USD:.2f} |",
        f"| **Utilisation** | {(total_cost / DAILY_BUDGET_USD * 100) if DAILY_BUDGET_USD > 0 else 0:.1f}% |",
        "",
        "#### Breakdown by Model",
        "",
        "| Model | Requests | Prompt Tokens | Completion Tokens | Cost (USD) |",
        "|-------|----------|---------------|-------------------|------------|",
    ]

    for model_name in sorted(model_costs.keys()):
        m = model_costs[model_name]
        lines.append(
            f"| {m['model']} | {m['request_count']:,} | "
            f"{m['total_prompt_tokens']:,} | {m['total_completion_tokens']:,} | "
            f"${m['total_cost_usd']:.4f} |"
        )

    if not model_costs:
        lines.append("| _(no traffic)_ | -- | -- | -- | -- |")

    message = "\n".join(lines)

    if not MATTERMOST_WEBHOOK_URL:
        logger.warning("mattermost_webhook_not_configured")
        return

    payload = {
        "channel": "costs",
        "username": "AI Gateway Cost Tracker",
        "icon_emoji": ":robot:",
        "text": message,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(MATTERMOST_WEBHOOK_URL, json=payload)
            if resp.status_code >= 400:
                logger.error("mattermost_post_failed", status=resp.status_code, body=resp.text[:300])
            else:
                logger.info("daily_summary_posted", date=str(yesterday), cost_usd=total_cost)
    except httpx.HTTPError as exc:
        logger.error("mattermost_post_error", error=str(exc))


# ──────────────────────────────────────────────────────────
# Application lifespan
# ──────────────────────────────────────────────────────────

langfuse_client: Optional[LangfuseClient] = None
scheduler: Optional[AsyncIOScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown of shared resources."""
    global langfuse_client, scheduler

    langfuse_client = LangfuseClient()
    logger.info("langfuse_client_initialized", host=LANGFUSE_HOST)

    # Schedule the daily summary at midnight UTC
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _post_daily_summary,
        trigger=CronTrigger(hour=0, minute=5),
        args=[langfuse_client],
        id="daily_cost_summary",
        name="Daily cost summary to Mattermost",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info("scheduler_started", job="daily_cost_summary", time="00:05 UTC")

    yield

    # Shutdown
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
    if langfuse_client:
        await langfuse_client.close()
        logger.info("langfuse_client_closed")


# ──────────────────────────────────────────────────────────
# FastAPI application
# ──────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Gateway Cost Tracker",
    description="Monitors and reports AI model usage costs for the Omni Quantum Elite system.",
    version="1.0.0",
    lifespan=lifespan,
)


# ─────────────── Health / Ready / Metrics ─────────────────

@app.get("/health", tags=["infrastructure"])
async def health() -> dict:
    """Liveness probe -- always returns OK if the process is running."""
    return {"status": "healthy", "service": "cost-tracker", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/ready", tags=["infrastructure"])
async def ready() -> JSONResponse:
    """Readiness probe -- verifies connectivity to Langfuse."""
    checks: dict[str, str] = {}

    # Check Langfuse reachability
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LANGFUSE_HOST}/api/public/health")
            checks["langfuse"] = "ok" if resp.status_code < 400 else f"http_{resp.status_code}"
    except httpx.HTTPError:
        checks["langfuse"] = "unreachable"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )


@app.get("/metrics", tags=["infrastructure"])
async def metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        content=generate_latest(registry).decode("utf-8"),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ─────────────── Cost endpoints ──────────────────────────

@app.get("/costs/today", tags=["costs"])
async def costs_today() -> dict:
    """Return today's total costs broken down by model."""
    start = time.monotonic()
    today = date.today()
    start_ts = _start_of_day(today)
    end_ts = _end_of_day(today)

    generations = await langfuse_client.fetch_all_generations(start_ts, end_ts)
    model_costs = _aggregate_by_model(generations)

    total_cost = sum(m["total_cost_usd"] for m in model_costs.values())
    total_requests = sum(m["request_count"] for m in model_costs.values())

    # Update Prometheus gauges
    for model_name, data in model_costs.items():
        COST_DAILY.labels(model=model_name).set(data["total_cost_usd"])
        TOKENS_TOTAL.labels(model=model_name, direction="input").inc(data["total_prompt_tokens"])
        TOKENS_TOTAL.labels(model=model_name, direction="output").inc(data["total_completion_tokens"])

    duration = time.monotonic() - start
    REQUEST_LATENCY.labels(endpoint="/costs/today").observe(duration)

    return {
        "date": today.isoformat(),
        "total_cost_usd": round(total_cost, 6),
        "total_requests": total_requests,
        "budget_daily_usd": DAILY_BUDGET_USD,
        "utilisation_pct": round((total_cost / DAILY_BUDGET_USD * 100) if DAILY_BUDGET_USD > 0 else 0, 2),
        "models": list(model_costs.values()),
    }


@app.get("/costs/range", tags=["costs"])
async def costs_range(
    start: date = Query(..., description="Start date (inclusive), YYYY-MM-DD"),
    end: date = Query(..., description="End date (inclusive), YYYY-MM-DD"),
) -> dict:
    """Return costs for a date range broken down by model and day."""
    timer_start = time.monotonic()
    start_ts = _start_of_day(start)
    end_ts = _end_of_day(end)

    generations = await langfuse_client.fetch_all_generations(start_ts, end_ts)

    # Aggregate by day + model
    daily: dict[str, dict[str, dict[str, Any]]] = {}
    for gen in generations:
        gen_time = gen.get("startTime", gen.get("createdAt", ""))
        if not gen_time:
            continue
        try:
            day_str = gen_time[:10]
        except (TypeError, IndexError):
            continue

        model = gen.get("model", "unknown")
        usage = gen.get("usage", {}) or {}
        prompt_tokens = usage.get("input", 0) or 0
        completion_tokens = usage.get("output", 0) or 0
        cost = _calc_cost(model, prompt_tokens, completion_tokens)

        if day_str not in daily:
            daily[day_str] = {}
        if model not in daily[day_str]:
            daily[day_str][model] = {
                "model": model,
                "total_cost_usd": 0.0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "request_count": 0,
            }
        entry = daily[day_str][model]
        entry["total_cost_usd"] = round(entry["total_cost_usd"] + cost, 8)
        entry["total_prompt_tokens"] += prompt_tokens
        entry["total_completion_tokens"] += completion_tokens
        entry["request_count"] += 1

    # Build sorted response
    days_list = []
    grand_total = 0.0
    for day_str in sorted(daily.keys()):
        models_for_day = list(daily[day_str].values())
        day_total = sum(m["total_cost_usd"] for m in models_for_day)
        grand_total += day_total
        days_list.append({
            "date": day_str,
            "total_cost_usd": round(day_total, 6),
            "models": models_for_day,
        })

    duration = time.monotonic() - timer_start
    REQUEST_LATENCY.labels(endpoint="/costs/range").observe(duration)

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "grand_total_cost_usd": round(grand_total, 6),
        "total_requests": sum(g.get("request_count", 0) for day_data in daily.values() for g in day_data.values()),
        "days": days_list,
    }


@app.get("/costs/by-service", tags=["costs"])
async def costs_by_service() -> dict:
    """Return current month's costs grouped by calling service."""
    timer_start = time.monotonic()
    start_ts = _start_of_month()
    end_ts = _end_of_day(date.today())

    generations = await langfuse_client.fetch_all_generations(start_ts, end_ts)
    service_costs = _aggregate_by_service(generations)

    total_cost = sum(s["total_cost_usd"] for s in service_costs.values())

    # Update Prometheus cost counters per service
    for service_name, data in service_costs.items():
        for model_name in data.get("models_used", []):
            COST_TOTAL.labels(model=model_name, service=service_name)

    duration = time.monotonic() - timer_start
    REQUEST_LATENCY.labels(endpoint="/costs/by-service").observe(duration)

    return {
        "period": "current_month",
        "start": _start_of_month()[:10],
        "end": date.today().isoformat(),
        "total_cost_usd": round(total_cost, 6),
        "services": list(service_costs.values()),
    }


@app.get("/budget/status", tags=["budget"])
async def budget_status() -> dict:
    """Return current budget utilisation vs configured limits."""
    timer_start = time.monotonic()

    # Fetch today's data
    today = date.today()
    today_gens = await langfuse_client.fetch_all_generations(
        _start_of_day(today), _end_of_day(today)
    )
    today_costs = _aggregate_by_model(today_gens)
    daily_total = sum(m["total_cost_usd"] for m in today_costs.values())

    # Fetch current month's data
    month_gens = await langfuse_client.fetch_all_generations(
        _start_of_month(), _end_of_day(today)
    )
    month_costs = _aggregate_by_model(month_gens)
    monthly_total = sum(m["total_cost_usd"] for m in month_costs.values())

    daily_pct = round((daily_total / DAILY_BUDGET_USD * 100) if DAILY_BUDGET_USD > 0 else 0, 2)
    monthly_pct = round((monthly_total / MONTHLY_BUDGET_USD * 100) if MONTHLY_BUDGET_USD > 0 else 0, 2)

    # Update Prometheus gauges
    BUDGET_UTILISATION.labels(period="daily").set(daily_pct)
    BUDGET_UTILISATION.labels(period="monthly").set(monthly_pct)

    # Determine alert level
    alert_level = "normal"
    if daily_pct >= 100 or monthly_pct >= 100:
        alert_level = "critical"
    elif daily_pct >= 80 or monthly_pct >= 80:
        alert_level = "warning"

    duration = time.monotonic() - timer_start
    REQUEST_LATENCY.labels(endpoint="/budget/status").observe(duration)

    return {
        "alert_level": alert_level,
        "daily": {
            "spent_usd": round(daily_total, 6),
            "budget_usd": DAILY_BUDGET_USD,
            "utilisation_pct": daily_pct,
            "remaining_usd": round(max(0, DAILY_BUDGET_USD - daily_total), 6),
        },
        "monthly": {
            "spent_usd": round(monthly_total, 6),
            "budget_usd": MONTHLY_BUDGET_USD,
            "utilisation_pct": monthly_pct,
            "remaining_usd": round(max(0, MONTHLY_BUDGET_USD - monthly_total), 6),
        },
        "top_models_today": [
            {"model": m["model"], "cost_usd": round(m["total_cost_usd"], 6), "requests": m["request_count"]}
            for m in sorted(today_costs.values(), key=lambda x: x["total_cost_usd"], reverse=True)[:5]
        ],
    }


# ──────────────────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=4001,
        log_level="info",
        access_log=True,
    )
