"""
Omni Quantum Elite — Master Orchestrator API
=============================================
The unified control plane for all 36 systems.

Endpoints:
  GET  /health                  — Orchestrator health
  GET  /api/v1/status           — Full platform status (all 36 systems)
  GET  /api/v1/status/{id}      — Single system status
  GET  /api/v1/overview         — Executive summary
  GET  /api/v1/topology         — Dependency graph
  POST /api/v1/action/{action}  — Execute platform actions
  GET  /api/v1/events           — SSE event stream
  GET  /api/v1/search           — Search across all systems
  GET  /metrics                 — Prometheus metrics
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import AsyncGenerator

import docker
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.responses import Response
from pydantic import BaseModel

from service_registry import (
    SERVICES,
    SERVICE_BY_ID,
    SERVICE_BY_CODENAME,
    ServiceDef,
    Tier,
    get_services_by_tier,
    get_services_by_tag,
    get_dependency_order,
)

# =============================================================================
# Config
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PORT = int(os.getenv("ORCHESTRATOR_PORT", "9500"))
REDIS_URL = os.getenv("REDIS_URL", "redis://omni-redis:6379/5")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK", "")
OMI_WEBHOOK = os.getenv("OMI_WEBHOOK", "")

logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("omni-orchestrator")

# =============================================================================
# Prometheus Metrics
# =============================================================================
PLATFORM_SERVICES_UP = Gauge("omni_platform_services_up", "Number of healthy services")
PLATFORM_SERVICES_TOTAL = Gauge("omni_platform_services_total", "Total registered services")
SERVICE_HEALTH = Gauge("omni_service_health", "Service health (1=up, 0=down)", ["service", "tier"])
HEALTH_CHECK_DURATION = Histogram("omni_health_check_seconds", "Health check duration", ["service"])
API_REQUESTS = Counter("omni_orchestrator_requests_total", "API requests", ["endpoint", "method"])
ACTION_COUNTER = Counter("omni_orchestrator_actions_total", "Actions executed", ["action"])
PLATFORM_SERVICES_TOTAL.set(len(SERVICES))

# =============================================================================
# State
# =============================================================================
class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"

service_statuses: dict[int, dict] = {}
platform_events: list[dict] = []
health_check_task = None
event_subscribers: list[asyncio.Queue] = []

# =============================================================================
# Helpers
# =============================================================================
async def check_service_health(svc: ServiceDef) -> dict:
    """Check a single service's health and return status dict."""
    url_env = os.getenv(svc.env_key, "")
    if not url_env:
        # Fallback: construct from container name
        url_env = f"http://{svc.container}:{svc.port}" if svc.container else ""

    if not url_env:
        return {
            "id": svc.id, "name": svc.name, "codename": svc.codename,
            "status": ServiceStatus.UNKNOWN, "tier": svc.tier.value,
            "latency_ms": 0, "message": "No endpoint configured",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    health_url = f"{url_env.rstrip('/')}{svc.health_path}"
    start = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(health_url)
            latency = round((time.monotonic() - start) * 1000, 1)

            if resp.status_code < 400:
                status = ServiceStatus.HEALTHY
                message = "OK"
            elif resp.status_code < 500:
                status = ServiceStatus.DEGRADED
                message = f"HTTP {resp.status_code}"
            else:
                status = ServiceStatus.DOWN
                message = f"HTTP {resp.status_code}"
    except httpx.ConnectError:
        latency = round((time.monotonic() - start) * 1000, 1)
        status = ServiceStatus.DOWN
        message = "Connection refused"
    except httpx.TimeoutException:
        latency = round((time.monotonic() - start) * 1000, 1)
        status = ServiceStatus.DOWN
        message = "Timeout"
    except Exception as e:
        latency = round((time.monotonic() - start) * 1000, 1)
        status = ServiceStatus.DOWN
        message = str(e)[:120]

    HEALTH_CHECK_DURATION.labels(service=svc.codename).observe(latency / 1000)
    health_val = 1.0 if status == ServiceStatus.HEALTHY else (0.5 if status == ServiceStatus.DEGRADED else 0.0)
    SERVICE_HEALTH.labels(service=svc.codename, tier=svc.tier.value).set(health_val)

    return {
        "id": svc.id, "name": svc.name, "codename": svc.codename,
        "status": status.value, "tier": svc.tier.value,
        "latency_ms": latency, "message": message,
        "tags": svc.tags, "port": svc.port,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def check_all_services() -> dict[int, dict]:
    """Check all 36 services concurrently."""
    tasks = [check_service_health(svc) for svc in SERVICES]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    statuses = {}
    for r in results:
        if isinstance(r, dict):
            statuses[r["id"]] = r
    return statuses


async def periodic_health_check():
    """Background task: check all services every 30 seconds."""
    global service_statuses
    while True:
        try:
            new_statuses = await check_all_services()

            # Detect state changes → emit events
            for sid, new in new_statuses.items():
                old = service_statuses.get(sid, {})
                if old.get("status") != new["status"] and old.get("status") is not None:
                    event = {
                        "type": "status_change",
                        "service_id": sid,
                        "service": new["codename"],
                        "from": old.get("status", "unknown"),
                        "to": new["status"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    platform_events.append(event)
                    if len(platform_events) > 1000:
                        platform_events.pop(0)

                    # Push to SSE subscribers
                    for q in event_subscribers:
                        try:
                            q.put_nowait(event)
                        except asyncio.QueueFull:
                            pass

                    # Alert on critical services going down
                    if new["tier"] == "critical" and new["status"] == "down":
                        await send_alert(
                            f"🚨 CRITICAL: **{new['name']}** is DOWN — {new['message']}",
                            severity="critical",
                        )

            service_statuses = new_statuses
            up_count = sum(1 for s in new_statuses.values() if s["status"] == "healthy")
            PLATFORM_SERVICES_UP.set(up_count)

        except Exception as e:
            logger.error(f"Health check cycle failed: {e}")

        await asyncio.sleep(30)


async def send_alert(message: str, severity: str = "info"):
    """Send alert to Mattermost + Omi."""
    icon = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(severity, "ℹ️")
    full_msg = f"{icon} **[Omni Command]** {message}"

    async with httpx.AsyncClient(timeout=5) as client:
        if MATTERMOST_WEBHOOK:
            try:
                await client.post(MATTERMOST_WEBHOOK, json={"text": full_msg})
            except Exception as e:
                logger.error(f"Mattermost alert failed: {e}")

        if OMI_WEBHOOK:
            try:
                await client.post(OMI_WEBHOOK, json={"message": message, "severity": severity})
            except Exception as e:
                logger.error(f"Omi alert failed: {e}")


def compute_overview(statuses: dict[int, dict]) -> dict:
    """Compute executive summary of platform health."""
    total = len(SERVICES)
    healthy = sum(1 for s in statuses.values() if s.get("status") == "healthy")
    degraded = sum(1 for s in statuses.values() if s.get("status") == "degraded")
    down = sum(1 for s in statuses.values() if s.get("status") == "down")
    unknown = total - healthy - degraded - down

    critical_svcs = get_services_by_tier(Tier.CRITICAL)
    critical_up = sum(
        1 for s in critical_svcs
        if statuses.get(s.id, {}).get("status") == "healthy"
    )

    if down == 0 and degraded == 0:
        platform_status = "operational"
        emoji = "🟢"
    elif down == 0 and degraded > 0:
        platform_status = "degraded"
        emoji = "🟡"
    elif critical_up == len(critical_svcs):
        platform_status = "partial_outage"
        emoji = "🟠"
    else:
        platform_status = "major_outage"
        emoji = "🔴"

    tier_summary = {}
    for tier in Tier:
        tier_svcs = get_services_by_tier(tier)
        tier_up = sum(1 for s in tier_svcs if statuses.get(s.id, {}).get("status") == "healthy")
        tier_summary[tier.value] = {"total": len(tier_svcs), "healthy": tier_up}

    return {
        "platform_status": platform_status,
        "emoji": emoji,
        "total_services": total,
        "healthy": healthy,
        "degraded": degraded,
        "down": down,
        "unknown": unknown,
        "uptime_pct": round(healthy / total * 100, 1) if total > 0 else 0,
        "critical_services": tier_summary.get("critical", {}),
        "tier_summary": tier_summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Application
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global health_check_task
    logger.info("🚀 Omni Command — Master Orchestrator starting...")
    logger.info(f"   Registered {len(SERVICES)} systems across {len(Tier)} tiers")

    # Start periodic health checks
    health_check_task = asyncio.create_task(periodic_health_check())

    yield

    if health_check_task:
        health_check_task.cancel()
    logger.info("Omni Command shutting down.")


app = FastAPI(
    title="Omni Command — Master Orchestrator",
    description="Unified control plane for the Omni Quantum Elite AI Coding System (36 services)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Middleware
# =============================================================================
@app.middleware("http")
async def track_requests(request: Request, call_next):
    API_REQUESTS.labels(endpoint=request.url.path, method=request.method).inc()
    return await call_next(request)


# =============================================================================
# Endpoints
# =============================================================================
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "omni-orchestrator",
        "version": "1.0.0",
        "registered_services": len(SERVICES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/status")
async def get_all_status(
    tier: str | None = Query(None, description="Filter by tier: critical, high, standard"),
    tag: str | None = Query(None, description="Filter by tag"),
):
    """Full platform status — all 36 systems."""
    statuses = dict(service_statuses)

    if not statuses:
        statuses = await check_all_services()

    results = list(statuses.values())

    if tier:
        results = [s for s in results if s.get("tier") == tier]
    if tag:
        results = [s for s in results if tag in s.get("tags", [])]

    return {
        "services": sorted(results, key=lambda x: x["id"]),
        "overview": compute_overview(statuses),
    }


@app.get("/api/v1/status/{service_id}")
async def get_service_status(service_id: int):
    """Single system status by ID."""
    svc = SERVICE_BY_ID.get(service_id)
    if not svc:
        raise HTTPException(404, f"System {service_id} not found")

    result = await check_service_health(svc)
    return result


@app.get("/api/v1/status/name/{codename}")
async def get_service_by_name(codename: str):
    """Single system status by codename."""
    svc = SERVICE_BY_CODENAME.get(codename)
    if not svc:
        raise HTTPException(404, f"System '{codename}' not found")

    result = await check_service_health(svc)
    return result


@app.get("/api/v1/overview")
async def get_overview():
    """Executive summary of platform health."""
    statuses = dict(service_statuses)
    if not statuses:
        statuses = await check_all_services()
    return compute_overview(statuses)


@app.get("/api/v1/topology")
async def get_topology():
    """Service dependency graph."""
    nodes = []
    edges = []
    for svc in SERVICES:
        nodes.append({
            "id": svc.id,
            "name": svc.name,
            "codename": svc.codename,
            "tier": svc.tier.value,
            "tags": svc.tags,
            "status": service_statuses.get(svc.id, {}).get("status", "unknown"),
        })
        for dep_id in svc.depends_on:
            edges.append({"from": dep_id, "to": svc.id})

    return {"nodes": nodes, "edges": edges}


@app.get("/api/v1/registry")
async def get_registry():
    """Full service registry metadata."""
    return {
        "services": [
            {
                "id": s.id, "name": s.name, "codename": s.codename,
                "description": s.description, "tier": s.tier.value,
                "tags": s.tags, "port": s.port, "container": s.container,
                "depends_on": s.depends_on,
                "health_path": s.health_path,
            }
            for s in SERVICES
        ],
        "total": len(SERVICES),
        "tiers": {t.value: len(get_services_by_tier(t)) for t in Tier},
    }


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
class ActionRequest(BaseModel):
    target: str | None = None  # service codename or "all"
    params: dict | None = None


@app.post("/api/v1/action/refresh")
async def action_refresh():
    """Force refresh health status of all services."""
    global service_statuses
    service_statuses = await check_all_services()
    ACTION_COUNTER.labels(action="refresh").inc()
    overview = compute_overview(service_statuses)
    return {"action": "refresh", "result": overview}


@app.post("/api/v1/action/restart")
async def action_restart(req: ActionRequest):
    """Restart a Docker container by service codename."""
    if not req.target:
        raise HTTPException(400, "target (service codename) required")

    svc = SERVICE_BY_CODENAME.get(req.target)
    if not svc:
        raise HTTPException(404, f"Service '{req.target}' not found")

    try:
        client = docker.from_env()
        container = client.containers.get(svc.container)
        container.restart(timeout=30)
        ACTION_COUNTER.labels(action="restart").inc()

        await send_alert(f"🔄 Restarted **{svc.name}** ({svc.container})", severity="info")

        return {
            "action": "restart",
            "service": svc.codename,
            "container": svc.container,
            "result": "restarting",
        }
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container '{svc.container}' not found")
    except Exception as e:
        raise HTTPException(500, f"Restart failed: {str(e)}")


@app.post("/api/v1/action/backup")
async def action_backup(req: ActionRequest):
    """Trigger a backup for a service via Backup Orchestrator (System 32)."""
    target = req.target or "all"
    backup_url = os.getenv("BACKUP_ORCHESTRATOR_URL", "http://omni-backup-orchestrator:9321")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{backup_url}/backup/{target}")
            resp.raise_for_status()
            ACTION_COUNTER.labels(action="backup").inc()
            return {"action": "backup", "target": target, "result": resp.json()}
    except Exception as e:
        raise HTTPException(500, f"Backup trigger failed: {str(e)}")


@app.post("/api/v1/action/rotate-secrets")
async def action_rotate_secrets(req: ActionRequest):
    """Trigger secret rotation via Rotation Agent (System 33)."""
    target = req.target or "all"
    rotation_url = os.getenv("ROTATION_AGENT_URL", "http://omni-secret-rotation:9331")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if target == "all":
                resp = await client.post(f"{rotation_url}/rotate-all")
            else:
                resp = await client.post(f"{rotation_url}/rotate/{target}")
            resp.raise_for_status()
            ACTION_COUNTER.labels(action="rotate-secrets").inc()
            return {"action": "rotate-secrets", "target": target, "result": resp.json()}
    except Exception as e:
        raise HTTPException(500, f"Secret rotation failed: {str(e)}")


@app.post("/api/v1/action/deploy")
async def action_deploy(req: ActionRequest):
    """Trigger deployment via Coolify (System 18)."""
    if not req.target:
        raise HTTPException(400, "target (project/app name) required")

    coolify_url = os.getenv("COOLIFY_URL", "http://omni-coolify:8000")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{coolify_url}/api/v1/deploy",
                json={"uuid": req.target},
                headers={"Authorization": f"Bearer {os.getenv('COOLIFY_TOKEN', '')}"},
            )
            resp.raise_for_status()
            ACTION_COUNTER.labels(action="deploy").inc()
            return {"action": "deploy", "target": req.target, "result": resp.json()}
    except Exception as e:
        raise HTTPException(500, f"Deploy failed: {str(e)}")


# ---------------------------------------------------------------------------
# Events (SSE)
# ---------------------------------------------------------------------------
@app.get("/api/v1/events")
async def event_stream():
    """Server-Sent Events stream for real-time platform events."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    event_subscribers.append(queue)

    async def generate() -> AsyncGenerator[str, None]:
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_subscribers.remove(queue)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/v1/events/history")
async def event_history(limit: int = Query(50, ge=1, le=500)):
    """Recent platform events."""
    return {"events": platform_events[-limit:]}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
@app.get("/api/v1/search")
async def search_services(q: str = Query(..., min_length=1)):
    """Search services by name, codename, tag, or description."""
    q_lower = q.lower()
    results = []
    for svc in SERVICES:
        score = 0
        if q_lower == svc.codename:
            score = 100
        elif q_lower in svc.name.lower():
            score = 80
        elif q_lower in svc.codename:
            score = 70
        elif any(q_lower == t for t in svc.tags):
            score = 60
        elif q_lower in svc.description.lower():
            score = 40
        elif any(q_lower in t for t in svc.tags):
            score = 30

        if score > 0:
            results.append({
                "id": svc.id, "name": svc.name, "codename": svc.codename,
                "description": svc.description, "tier": svc.tier.value,
                "tags": svc.tags, "score": score,
                "status": service_statuses.get(svc.id, {}).get("status", "unknown"),
            })

    results.sort(key=lambda x: -x["score"])
    return {"query": q, "results": results}


# ---------------------------------------------------------------------------
# Docker Info
# ---------------------------------------------------------------------------
@app.get("/api/v1/docker/containers")
async def list_containers():
    """List all Docker containers with omni.quantum labels."""
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True, filters={"label": "omni.quantum.system"})
        return {
            "containers": [
                {
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "unknown",
                    "labels": {k: v for k, v in c.labels.items() if k.startswith("omni.")},
                    "created": c.attrs.get("Created", ""),
                }
                for c in containers
            ]
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/v1/docker/stats")
async def docker_stats():
    """Docker host resource usage."""
    try:
        client = docker.from_env()
        info = client.info()
        return {
            "containers_running": info.get("ContainersRunning", 0),
            "containers_stopped": info.get("ContainersStopped", 0),
            "containers_paused": info.get("ContainersPaused", 0),
            "images": info.get("Images", 0),
            "cpu_count": info.get("NCPU", 0),
            "memory_bytes": info.get("MemTotal", 0),
            "memory_gb": round(info.get("MemTotal", 0) / (1024**3), 1),
            "docker_version": info.get("ServerVersion", ""),
            "os": info.get("OperatingSystem", ""),
            "kernel": info.get("KernelVersion", ""),
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# Prometheus
# ---------------------------------------------------------------------------
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
