"""
Omni Quantum Elite — SLA Tracker Service
Tracks SLO compliance, error budgets, and SLA violations across all services.
Persists data in PostgreSQL and exposes Prometheus metrics.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import asyncpg
import httpx
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram, generate_latest

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sla-tracker")

app = FastAPI(title="Omni Quantum SLA Tracker", version="1.0.0")

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://omni-prometheus:9090")
POSTGRES_URL = os.getenv("POSTGRES_URL", "")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK", "")
OMI_WEBHOOK = os.getenv("OMI_WEBHOOK_URL", "")

# Prometheus metrics
sla_uptime = Gauge("sla_uptime_percent", "Current uptime percentage", ["service", "tier"])
sla_error_budget = Gauge("sla_error_budget_remaining_percent", "Error budget remaining %", ["service", "tier"])
sla_violations = Counter("sla_violations_total", "Total SLA violations", ["service", "tier"])
sla_check_duration = Histogram("sla_check_duration_seconds", "SLA check duration")

db_pool: asyncpg.Pool | None = None
sla_defs: dict = {}
scheduler = AsyncIOScheduler()


async def init_db():
    """Initialize database connection and schema."""
    global db_pool
    if POSTGRES_URL:
        db_pool = await asyncpg.create_pool(POSTGRES_URL, min_size=2, max_size=10)
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sla_measurements (
                    id BIGSERIAL PRIMARY KEY,
                    service_name VARCHAR(128) NOT NULL,
                    tier VARCHAR(32) NOT NULL,
                    measured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_healthy BOOLEAN NOT NULL,
                    response_time_ms FLOAT,
                    uptime_percent FLOAT,
                    error_budget_remaining FLOAT
                );
                CREATE INDEX IF NOT EXISTS idx_sla_service_time
                    ON sla_measurements(service_name, measured_at DESC);
            """)
        logger.info("SLA database initialized")


def load_sla_definitions():
    """Load SLA definitions from YAML config."""
    global sla_defs
    config_path = "/app/sla-definitions.yml"
    if os.path.exists(config_path):
        with open(config_path) as f:
            sla_defs = yaml.safe_load(f)
        logger.info(f"Loaded SLA definitions: {len(sla_defs.get('sla_definitions', {}))} tiers")
    else:
        logger.warning("No SLA definitions file found")


async def check_service_health(service: dict) -> tuple[bool, float]:
    """Check a single service's health. Returns (is_healthy, response_time_ms)."""
    endpoint = service["endpoint"]
    check_type = service.get("check_type", "http")
    start = time.monotonic()

    try:
        if check_type == "http":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(endpoint)
                elapsed = (time.monotonic() - start) * 1000
                return resp.status_code < 500, elapsed
        elif check_type == "tcp":
            # Parse host:port from endpoint
            parts = endpoint.replace("http://", "").replace("https://", "").split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 80
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=10
            )
            elapsed = (time.monotonic() - start) * 1000
            writer.close()
            await writer.wait_closed()
            return True, elapsed
    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        return False, elapsed

    return False, 0.0


async def calculate_uptime(service_name: str, window_days: int = 30) -> float:
    """Calculate uptime percentage from stored measurements."""
    if not db_pool:
        return 100.0
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_healthy) as healthy
            FROM sla_measurements
            WHERE service_name = $1
              AND measured_at > NOW() - INTERVAL '%s days'
        """ % window_days, service_name)
        if row and row["total"] > 0:
            return (row["healthy"] / row["total"]) * 100
    return 100.0


async def run_sla_checks():
    """Run SLA checks across all defined services."""
    definitions = sla_defs.get("sla_definitions", {})

    for tier_name, tier_config in definitions.items():
        target_uptime = tier_config.get("target_uptime", 99.0)
        window = tier_config.get("error_budget_window", "30d")
        window_days = int(window.replace("d", ""))

        for service in tier_config.get("services", []):
            with sla_check_duration.time():
                name = service["name"]
                is_healthy, response_ms = await check_service_health(service)

                # Store measurement
                if db_pool:
                    async with db_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO sla_measurements
                            (service_name, tier, is_healthy, response_time_ms)
                            VALUES ($1, $2, $3, $4)
                        """, name, tier_name, is_healthy, response_ms)

                # Calculate current uptime
                uptime = await calculate_uptime(name, window_days)
                sla_uptime.labels(service=name, tier=tier_name).set(uptime)

                # Calculate error budget
                error_budget_total = 100 - target_uptime  # e.g., 0.1% for 99.9%
                error_budget_used = 100 - uptime
                error_budget_remaining = ((error_budget_total - error_budget_used) / error_budget_total) * 100
                sla_error_budget.labels(service=name, tier=tier_name).set(error_budget_remaining)

                # Check for violations
                if uptime < target_uptime:
                    sla_violations.labels(service=name, tier=tier_name).inc()
                    await alert_sla_violation(name, tier_name, uptime, target_uptime, error_budget_remaining)

                logger.debug(
                    f"SLA check: {name} [{tier_name}] healthy={is_healthy} "
                    f"uptime={uptime:.3f}% budget={error_budget_remaining:.1f}%"
                )


async def alert_sla_violation(service: str, tier: str, uptime: float, target: float, budget: float):
    """Alert on SLA violations."""
    if MATTERMOST_WEBHOOK:
        payload = {
            "username": "SLA Tracker",
            "icon_emoji": ":warning:",
            "text": (
                f"### 🚨 SLA Violation: {service}\n"
                f"| Field | Value |\n|---|---|\n"
                f"| Service | `{service}` |\n"
                f"| Tier | {tier} |\n"
                f"| Current Uptime | {uptime:.3f}% |\n"
                f"| Target | {target}% |\n"
                f"| Error Budget | {budget:.1f}% remaining |\n"
            ),
        }
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                await client.post(MATTERMOST_WEBHOOK, json=payload)
            except Exception as e:
                logger.error(f"Mattermost alert failed: {e}")


@app.on_event("startup")
async def startup():
    load_sla_definitions()
    await init_db()
    scheduler.add_job(run_sla_checks, "interval", minutes=1, id="sla_checks")
    scheduler.start()
    logger.info("SLA Tracker started")


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
    if db_pool:
        await db_pool.close()


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/sla/status")
async def sla_status():
    """Get current SLA status for all services."""
    results = {}
    definitions = sla_defs.get("sla_definitions", {})
    for tier_name, tier_config in definitions.items():
        target = tier_config.get("target_uptime", 99.0)
        for service in tier_config.get("services", []):
            name = service["name"]
            uptime = await calculate_uptime(name)
            error_budget_total = 100 - target
            error_budget_used = max(0, 100 - uptime)
            budget_remaining = ((error_budget_total - error_budget_used) / error_budget_total) * 100
            results[name] = {
                "tier": tier_name,
                "target_uptime": target,
                "current_uptime": round(uptime, 4),
                "error_budget_remaining": round(budget_remaining, 2),
                "status": "OK" if uptime >= target else "VIOLATED",
            }
    return results


@app.get("/sla/report")
async def sla_report():
    """Generate SLA compliance report."""
    status = await sla_status()
    total = len(status)
    compliant = sum(1 for s in status.values() if s["status"] == "OK")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_services": total,
        "compliant": compliant,
        "violated": total - compliant,
        "compliance_rate": round((compliant / total * 100) if total else 0, 2),
        "services": status,
    }
