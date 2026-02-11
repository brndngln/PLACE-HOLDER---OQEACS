"""
══════════════════════════════════════════════════════════════════════════════
⚛ OMNI QUANTUM ELITE — Master Orchestrator API (System 37)
══════════════════════════════════════════════════════════════════════════════
Unified control plane for all 36 systems. Provides REST API for:
  - Service health monitoring & management
  - Pipeline orchestration (8-stage)
  - Event processing & notification routing
  - Knowledge base statistics
  - Platform metrics & SLA tracking
  - Docker container management
  - LLM routing & token tracking
══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import asyncpg
import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ─── Configuration ────────────────────────────────────────────────────────────

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://omni_orchestrator:password@omni-postgres:5432/omni_orchestrator")
REDIS_URL = os.getenv("REDIS_URL", "redis://omni-redis:6379/0")
OMNI_VERSION = os.getenv("OMNI_VERSION", "1.0.0")
OMNI_DOMAIN = os.getenv("OMNI_DOMAIN", "localhost")
PORT = int(os.getenv("PORT", "9500"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("omni.orchestrator")


# ─── Service Registry ────────────────────────────────────────────────────────

class ServiceTier(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    STANDARD = "STANDARD"


class ServiceDef(BaseModel):
    id: int
    name: str
    codename: str
    container: str
    port: int
    tier: ServiceTier
    health_url: str = ""
    tool: str = ""
    system_group: str = ""


SERVICE_REGISTRY: list[ServiceDef] = [
    # Foundation Layer (1-6)
    ServiceDef(id=1, name="Backup Fortress", codename="backup", container="omni-restic-server", port=8000, tier=ServiceTier.CRITICAL, tool="Restic", system_group="Foundation"),
    ServiceDef(id=2, name="Cryptographic Fortress", codename="vault", container="omni-vault", port=8200, tier=ServiceTier.CRITICAL, health_url="/v1/sys/health", tool="Vault", system_group="Foundation"),
    ServiceDef(id=3, name="AI Gateway", codename="litellm", container="omni-litellm", port=4000, tier=ServiceTier.CRITICAL, health_url="/health", tool="LiteLLM", system_group="Foundation"),
    ServiceDef(id=4, name="Security Nexus", codename="authentik", container="omni-authentik", port=9000, tier=ServiceTier.CRITICAL, health_url="/-/health/ready/", tool="Authentik", system_group="Foundation"),
    ServiceDef(id=5, name="Observatory", codename="prometheus", container="omni-prometheus", port=9090, tier=ServiceTier.CRITICAL, health_url="/-/healthy", tool="Prometheus", system_group="Foundation"),
    ServiceDef(id=6, name="Log Nexus", codename="loki", container="omni-loki", port=3100, tier=ServiceTier.HIGH, health_url="/ready", tool="Loki", system_group="Foundation"),
    # Development Layer (7-14)
    ServiceDef(id=7, name="Code Fortress", codename="gitea", container="omni-gitea", port=3000, tier=ServiceTier.CRITICAL, health_url="/api/v1/version", tool="Gitea", system_group="Development"),
    ServiceDef(id=8, name="Neural Network", codename="ollama", container="omni-ollama", port=11434, tier=ServiceTier.HIGH, health_url="/api/version", tool="Ollama", system_group="Development"),
    ServiceDef(id=9, name="Workflow Engine", codename="n8n", container="omni-n8n", port=5678, tier=ServiceTier.HIGH, health_url="/healthz", tool="n8n", system_group="Development"),
    ServiceDef(id=10, name="Communication Hub", codename="mattermost", container="omni-mattermost", port=8065, tier=ServiceTier.HIGH, health_url="/api/v4/system/ping", tool="Mattermost", system_group="Development"),
    ServiceDef(id=11, name="Vector Memory", codename="qdrant", container="omni-qdrant", port=6333, tier=ServiceTier.HIGH, health_url="/healthz", tool="Qdrant", system_group="Development"),
    ServiceDef(id=12, name="Object Store", codename="minio", container="omni-minio", port=9000, tier=ServiceTier.CRITICAL, health_url="/minio/health/live", tool="MinIO", system_group="Development"),
    ServiceDef(id=13, name="AI Observability", codename="langfuse", container="omni-langfuse", port=3000, tier=ServiceTier.HIGH, health_url="/api/public/health", tool="Langfuse", system_group="Development"),
    ServiceDef(id=14, name="Project Command", codename="plane", container="omni-plane-web", port=3000, tier=ServiceTier.STANDARD, tool="Plane", system_group="Development"),
    # Integration Layer (15-22)
    ServiceDef(id=15, name="Integration Hub", codename="nango", container="omni-nango", port=3003, tier=ServiceTier.HIGH, health_url="/health", tool="Nango", system_group="Integration"),
    ServiceDef(id=16, name="AI Coder Alpha", codename="openhands", container="omni-openhands", port=3000, tier=ServiceTier.HIGH, tool="OpenHands", system_group="Integration"),
    ServiceDef(id=17, name="AI Coder Beta", codename="swe-agent", container="omni-swe-agent", port=8000, tier=ServiceTier.HIGH, tool="SWE-Agent", system_group="Integration"),
    ServiceDef(id=18, name="Deploy Engine", codename="coolify", container="omni-coolify", port=8000, tier=ServiceTier.HIGH, tool="Coolify", system_group="Integration"),
    ServiceDef(id=19, name="Flow Builder", codename="flowise", container="omni-flowise", port=3000, tier=ServiceTier.STANDARD, tool="Flowise", system_group="Integration"),
    ServiceDef(id=20, name="Knowledge Base", codename="wikijs", container="omni-wikijs", port=3000, tier=ServiceTier.STANDARD, tool="Wiki.js", system_group="Integration"),
    ServiceDef(id=21, name="Analytics Engine", codename="superset", container="omni-superset", port=8088, tier=ServiceTier.STANDARD, tool="Superset", system_group="Integration"),
    ServiceDef(id=22, name="Schedule Manager", codename="calcom", container="omni-calcom", port=3000, tier=ServiceTier.STANDARD, tool="Cal.com", system_group="Integration"),
    # Business Layer (23-28)
    ServiceDef(id=23, name="CRM Hub", codename="twenty", container="omni-twenty", port=3000, tier=ServiceTier.STANDARD, tool="Twenty", system_group="Business"),
    ServiceDef(id=24, name="Invoice Manager", codename="crater", container="omni-crater", port=80, tier=ServiceTier.STANDARD, tool="Crater", system_group="Business"),
    ServiceDef(id=25, name="Security Shield", codename="crowdsec", container="omni-crowdsec", port=8080, tier=ServiceTier.HIGH, tool="CrowdSec", system_group="Business"),
    ServiceDef(id=26, name="Container Manager", codename="portainer", container="omni-portainer", port=9443, tier=ServiceTier.STANDARD, tool="Portainer", system_group="Business"),
    ServiceDef(id=27, name="Token Infinity", codename="token-infinity", container="omni-token-infinity", port=9600, tier=ServiceTier.CRITICAL, health_url="/health", tool="Custom", system_group="Business"),
    ServiceDef(id=28, name="Omi Wearable Bridge", codename="omi-bridge", container="omni-omi-bridge", port=9700, tier=ServiceTier.HIGH, health_url="/health", tool="Custom", system_group="Business"),
    # Enhanced Infrastructure (29-37)
    ServiceDef(id=29, name="Pulse Command Pro", codename="enhanced-monitoring", container="omni-thanos-query", port=9090, tier=ServiceTier.HIGH, health_url="/-/healthy", tool="Thanos", system_group="Enhanced"),
    ServiceDef(id=30, name="Log Nexus Pro", codename="enhanced-logging", container="omni-log-pattern-detector", port=9301, tier=ServiceTier.STANDARD, health_url="/health", tool="Custom", system_group="Enhanced"),
    ServiceDef(id=31, name="Guardian Eye", codename="uptime-monitor", container="omni-uptime-kuma", port=3001, tier=ServiceTier.HIGH, tool="Uptime Kuma", system_group="Enhanced"),
    ServiceDef(id=32, name="Backup Fortress Pro", codename="enhanced-backup", container="omni-backup-orchestrator", port=9321, tier=ServiceTier.HIGH, health_url="/health", tool="Custom", system_group="Enhanced"),
    ServiceDef(id=33, name="Cryptographic Fortress Pro", codename="enhanced-secrets", container="omni-secret-rotation", port=9331, tier=ServiceTier.HIGH, health_url="/health", tool="Custom", system_group="Enhanced"),
    ServiceDef(id=34, name="Gateway Sentinel Pro", codename="enhanced-proxy", container="omni-traefik", port=8080, tier=ServiceTier.CRITICAL, tool="Traefik", system_group="Enhanced"),
    ServiceDef(id=35, name="Build Forge", codename="cicd-pipelines", container="omni-woodpecker-server", port=8000, tier=ServiceTier.HIGH, health_url="/healthz", tool="Woodpecker", system_group="Enhanced"),
    ServiceDef(id=36, name="Code Forge", codename="dev-environments", container="omni-coder", port=7080, tier=ServiceTier.STANDARD, health_url="/api/v2/buildinfo", tool="Coder", system_group="Enhanced"),
    ServiceDef(id=37, name="Omni Command", codename="master-orchestrator", container="omni-orchestrator", port=9500, tier=ServiceTier.CRITICAL, health_url="/health", tool="Custom", system_group="Enhanced"),
]


# ─── Models ───────────────────────────────────────────────────────────────────

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    OFFLINE = "offline"


class ServiceHealth(BaseModel):
    service_id: int
    name: str
    codename: str
    container: str
    tier: ServiceTier
    status: HealthStatus
    response_time_ms: Optional[int] = None
    last_checked: str
    uptime_percent: Optional[float] = None
    details: dict = {}


class PlatformStatus(BaseModel):
    version: str
    domain: str
    timestamp: str
    total_services: int
    healthy: int
    unhealthy: int
    degraded: int
    offline: int
    uptime_percent: float
    services: list[ServiceHealth]


class PipelineRequest(BaseModel):
    project_name: str
    description: str
    language: str = "python"
    framework: str = ""
    pipeline_type: str = "full"


class PipelineStatus(BaseModel):
    id: str
    project_name: str
    status: str
    stage: str
    started_at: str
    duration_seconds: Optional[int] = None
    scores: dict = {}


class EventPayload(BaseModel):
    event_type: str
    source_system: str
    severity: str = "info"
    title: str
    details: dict = {}


# ─── Global State ─────────────────────────────────────────────────────────────

db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[aioredis.Redis] = None
http_client: Optional[httpx.AsyncClient] = None
health_cache: dict[int, ServiceHealth] = {}
boot_time = datetime.now(timezone.utc)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client, http_client

    logger.info("⚛ Omni Quantum Elite — Master Orchestrator starting...")

    # Connect to PostgreSQL
    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=30,
        )
        logger.info("✓ PostgreSQL connected")
    except Exception as e:
        logger.error(f"✗ PostgreSQL connection failed: {e}")

    # Connect to Redis
    try:
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("✓ Redis connected")
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")

    # HTTP client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
    logger.info("✓ HTTP client initialized")

    # Start background health checker
    health_task = asyncio.create_task(health_check_loop())

    logger.info(f"⚛ Orchestrator API ready on port {PORT}")

    yield

    # Shutdown
    health_task.cancel()
    if http_client:
        await http_client.aclose()
    if redis_client:
        await redis_client.close()
    if db_pool:
        await db_pool.close()

    logger.info("⚛ Orchestrator shutdown complete")


# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="⚛ Omni Quantum Elite — Master Orchestrator",
    description="Unified control plane for 37 microservices",
    version=OMNI_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health Check Loop ───────────────────────────────────────────────────────

async def check_service_health(svc: ServiceDef) -> ServiceHealth:
    """Check a single service's health."""
    start = time.monotonic()
    status = HealthStatus.UNKNOWN
    details = {}

    try:
        # Try health endpoint first
        if svc.health_url:
            url = f"http://{svc.container}:{svc.port}{svc.health_url}"
        else:
            url = f"http://{svc.container}:{svc.port}/"

        resp = await http_client.get(url)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if resp.status_code < 400:
            status = HealthStatus.HEALTHY
        elif resp.status_code < 500:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        details["status_code"] = resp.status_code
        details["response_time_ms"] = elapsed_ms

    except httpx.ConnectError:
        status = HealthStatus.OFFLINE
        elapsed_ms = int((time.monotonic() - start) * 1000)
        details["error"] = "connection_refused"
    except httpx.TimeoutException:
        status = HealthStatus.UNHEALTHY
        elapsed_ms = int((time.monotonic() - start) * 1000)
        details["error"] = "timeout"
    except Exception as e:
        status = HealthStatus.UNKNOWN
        elapsed_ms = int((time.monotonic() - start) * 1000)
        details["error"] = str(e)

    return ServiceHealth(
        service_id=svc.id,
        name=svc.name,
        codename=svc.codename,
        container=svc.container,
        tier=svc.tier,
        status=status,
        response_time_ms=elapsed_ms,
        last_checked=datetime.now(timezone.utc).isoformat(),
        details=details,
    )


async def health_check_loop():
    """Continuously check all service health."""
    while True:
        try:
            tasks = [check_service_health(svc) for svc in SERVICE_REGISTRY]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, ServiceHealth):
                    health_cache[result.service_id] = result

                    # Log to database
                    if db_pool:
                        try:
                            await db_pool.execute(
                                """INSERT INTO service_health_log
                                   (service_id, status, response_time_ms, details)
                                   VALUES ($1, $2, $3, $4)""",
                                result.codename,
                                result.status.value,
                                result.response_time_ms,
                                json.dumps(result.details),
                            )
                        except Exception:
                            pass

                    # Publish to Redis for real-time consumers
                    if redis_client:
                        try:
                            await redis_client.publish(
                                "omni:health",
                                json.dumps({
                                    "service_id": result.service_id,
                                    "status": result.status.value,
                                    "response_time_ms": result.response_time_ms,
                                    "timestamp": result.last_checked,
                                }),
                            )
                        except Exception:
                            pass

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Health check loop error: {e}")

        await asyncio.sleep(30)


# ══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

# ─── Health & Info ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Orchestrator's own health check."""
    checks = {
        "api": "ok",
        "database": "unknown",
        "redis": "unknown",
    }

    if db_pool:
        try:
            await db_pool.fetchval("SELECT 1")
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"

    if redis_client:
        try:
            await redis_client.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "error"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "healthy" if all_ok else "degraded",
            "checks": checks,
            "version": OMNI_VERSION,
            "uptime_seconds": int((datetime.now(timezone.utc) - boot_time).total_seconds()),
        },
    )


@app.get("/")
async def root():
    """Platform info."""
    return {
        "name": "⚛ Omni Quantum Elite",
        "component": "Master Orchestrator",
        "version": OMNI_VERSION,
        "domain": OMNI_DOMAIN,
        "services": len(SERVICE_REGISTRY),
        "endpoints": {
            "health": "/health",
            "platform_status": "/api/v1/platform/status",
            "services": "/api/v1/services",
            "pipelines": "/api/v1/pipelines",
            "events": "/api/v1/events",
            "docs": "/docs",
        },
    }


# ─── Platform Status ─────────────────────────────────────────────────────────

@app.get("/api/v1/platform/status", response_model=PlatformStatus)
async def platform_status():
    """Get full platform status with all service health."""
    services = list(health_cache.values())

    healthy = sum(1 for s in services if s.status == HealthStatus.HEALTHY)
    unhealthy = sum(1 for s in services if s.status == HealthStatus.UNHEALTHY)
    degraded = sum(1 for s in services if s.status == HealthStatus.DEGRADED)
    offline = sum(1 for s in services if s.status == HealthStatus.OFFLINE)

    total = len(SERVICE_REGISTRY)
    uptime_pct = (healthy / total * 100) if total > 0 else 0.0

    return PlatformStatus(
        version=OMNI_VERSION,
        domain=OMNI_DOMAIN,
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_services=total,
        healthy=healthy,
        unhealthy=unhealthy,
        degraded=degraded,
        offline=offline,
        uptime_percent=round(uptime_pct, 2),
        services=sorted(services, key=lambda s: s.service_id),
    )


# ─── Service Management ──────────────────────────────────────────────────────

@app.get("/api/v1/services")
async def list_services(
    tier: Optional[ServiceTier] = None,
    group: Optional[str] = None,
    status: Optional[HealthStatus] = None,
):
    """List all registered services with optional filtering."""
    results = []
    for svc in SERVICE_REGISTRY:
        if tier and svc.tier != tier:
            continue
        if group and svc.system_group.lower() != group.lower():
            continue

        health = health_cache.get(svc.id)
        if status and health and health.status != status:
            continue

        results.append({
            **svc.model_dump(),
            "health": health.model_dump() if health else None,
        })

    return {"count": len(results), "services": results}


@app.get("/api/v1/services/{service_id}")
async def get_service(service_id: int):
    """Get detailed info for a specific service."""
    svc = next((s for s in SERVICE_REGISTRY if s.id == service_id), None)
    if not svc:
        raise HTTPException(404, f"Service {service_id} not found")

    health = health_cache.get(svc.id)

    # Get recent health history
    history = []
    if db_pool:
        try:
            rows = await db_pool.fetch(
                """SELECT status, response_time_ms, checked_at
                   FROM service_health_log
                   WHERE service_id = $1
                   ORDER BY checked_at DESC LIMIT 100""",
                svc.codename,
            )
            history = [dict(r) for r in rows]
        except Exception:
            pass

    return {
        **svc.model_dump(),
        "health": health.model_dump() if health else None,
        "history": history,
    }


@app.post("/api/v1/services/{service_id}/restart")
async def restart_service(service_id: int, background_tasks: BackgroundTasks):
    """Request a service restart (delegates to Docker)."""
    svc = next((s for s in SERVICE_REGISTRY if s.id == service_id), None)
    if not svc:
        raise HTTPException(404, f"Service {service_id} not found")

    async def do_restart():
        import subprocess
        try:
            subprocess.run(
                ["docker", "restart", svc.container],
                timeout=60,
                capture_output=True,
            )
            logger.info(f"Restarted {svc.container}")
            await emit_event(EventPayload(
                event_type="service.restart",
                source_system="orchestrator",
                severity="warning",
                title=f"Service {svc.name} restarted",
                details={"service_id": svc.id, "container": svc.container},
            ))
        except Exception as e:
            logger.error(f"Failed to restart {svc.container}: {e}")

    background_tasks.add_task(do_restart)
    return {"status": "restart_initiated", "service": svc.name, "container": svc.container}


# ─── Pipeline Management ─────────────────────────────────────────────────────

@app.post("/api/v1/pipelines", response_model=PipelineStatus)
async def create_pipeline(req: PipelineRequest):
    """Create a new pipeline run."""
    if not db_pool:
        raise HTTPException(503, "Database not available")

    pipeline_id = await db_pool.fetchval(
        """INSERT INTO pipeline_runs (project_id, pipeline_type, status, stage)
           VALUES ($1, $2, 'pending', 'intent')
           RETURNING id""",
        req.project_name,
        req.pipeline_type,
    )

    await emit_event(EventPayload(
        event_type="pipeline.created",
        source_system="orchestrator",
        severity="info",
        title=f"Pipeline created for {req.project_name}",
        details={"pipeline_id": str(pipeline_id), "type": req.pipeline_type},
    ))

    return PipelineStatus(
        id=str(pipeline_id),
        project_name=req.project_name,
        status="pending",
        stage="intent",
        started_at=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/api/v1/pipelines")
async def list_pipelines(
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
):
    """List pipeline runs."""
    if not db_pool:
        raise HTTPException(503, "Database not available")

    if status:
        rows = await db_pool.fetch(
            """SELECT id, project_id, pipeline_type, status, stage,
                      started_at, completed_at, duration_seconds, scores
               FROM pipeline_runs WHERE status = $1
               ORDER BY started_at DESC LIMIT $2""",
            status, limit,
        )
    else:
        rows = await db_pool.fetch(
            """SELECT id, project_id, pipeline_type, status, stage,
                      started_at, completed_at, duration_seconds, scores
               FROM pipeline_runs ORDER BY started_at DESC LIMIT $1""",
            limit,
        )

    return {
        "count": len(rows),
        "pipelines": [
            {
                "id": str(r["id"]),
                "project_name": r["project_id"],
                "pipeline_type": r["pipeline_type"],
                "status": r["status"],
                "stage": r["stage"],
                "started_at": r["started_at"].isoformat() if r["started_at"] else None,
                "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                "duration_seconds": r["duration_seconds"],
                "scores": json.loads(r["scores"]) if r["scores"] else {},
            }
            for r in rows
        ],
    }


@app.get("/api/v1/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get pipeline details including agent handoffs."""
    if not db_pool:
        raise HTTPException(503, "Database not available")

    row = await db_pool.fetchrow(
        "SELECT * FROM pipeline_runs WHERE id = $1", pipeline_id,
    )
    if not row:
        raise HTTPException(404, f"Pipeline {pipeline_id} not found")

    handoffs = await db_pool.fetch(
        """SELECT from_agent, to_agent, handoff_data, created_at
           FROM agent_handoffs WHERE pipeline_run_id = $1
           ORDER BY created_at""",
        pipeline_id,
    )

    return {
        "id": str(row["id"]),
        "project_name": row["project_id"],
        "pipeline_type": row["pipeline_type"],
        "status": row["status"],
        "stage": row["stage"],
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
        "duration_seconds": row["duration_seconds"],
        "scores": json.loads(row["scores"]) if row["scores"] else {},
        "result": json.loads(row["result"]) if row["result"] else {},
        "handoffs": [
            {
                "from": h["from_agent"],
                "to": h["to_agent"],
                "data": json.loads(h["handoff_data"]) if h["handoff_data"] else {},
                "at": h["created_at"].isoformat(),
            }
            for h in handoffs
        ],
    }


# ─── Events ──────────────────────────────────────────────────────────────────

async def emit_event(event: EventPayload):
    """Emit an event to both database and Redis stream."""
    # Database
    if db_pool:
        try:
            await db_pool.execute(
                """INSERT INTO platform_events
                   (event_type, source_system, severity, title, details)
                   VALUES ($1, $2, $3, $4, $5)""",
                event.event_type,
                event.source_system,
                event.severity,
                event.title,
                json.dumps(event.details),
            )
        except Exception as e:
            logger.error(f"Failed to store event: {e}")

    # Redis stream
    if redis_client:
        try:
            await redis_client.xadd(
                "omni:events",
                {
                    "event_type": event.event_type,
                    "source": event.source_system,
                    "severity": event.severity,
                    "title": event.title,
                    "details": json.dumps(event.details),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                maxlen=10000,
            )
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")


@app.post("/api/v1/events")
async def create_event(event: EventPayload):
    """Receive and route an event."""
    await emit_event(event)
    return {"status": "accepted", "event_type": event.event_type}


@app.get("/api/v1/events")
async def list_events(
    severity: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(default=50, le=500),
):
    """List recent events."""
    if not db_pool:
        raise HTTPException(503, "Database not available")

    conditions = []
    params = []
    idx = 1

    if severity:
        conditions.append(f"severity = ${idx}")
        params.append(severity)
        idx += 1
    if source:
        conditions.append(f"source_system = ${idx}")
        params.append(source)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    rows = await db_pool.fetch(
        f"""SELECT id, event_type, source_system, severity, title, details,
                   acknowledged, created_at
            FROM platform_events {where}
            ORDER BY created_at DESC LIMIT ${idx}""",
        *params,
    )

    return {
        "count": len(rows),
        "events": [
            {
                "id": str(r["id"]),
                "event_type": r["event_type"],
                "source": r["source_system"],
                "severity": r["severity"],
                "title": r["title"],
                "details": json.loads(r["details"]) if r["details"] else {},
                "acknowledged": r["acknowledged"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ],
    }


# ─── Knowledge Stats ─────────────────────────────────────────────────────────

@app.get("/api/v1/knowledge/stats")
async def knowledge_stats():
    """Get knowledge base statistics from Qdrant."""
    stats = {"collections": [], "total_vectors": 0}

    try:
        resp = await http_client.get(
            f"{os.getenv('QDRANT_URL', 'http://omni-qdrant:6333')}/collections"
        )
        if resp.status_code == 200:
            data = resp.json()
            for coll in data.get("result", {}).get("collections", []):
                name = coll["name"]
                detail_resp = await http_client.get(
                    f"{os.getenv('QDRANT_URL', 'http://omni-qdrant:6333')}/collections/{name}"
                )
                if detail_resp.status_code == 200:
                    detail = detail_resp.json().get("result", {})
                    count = detail.get("points_count", 0)
                    stats["collections"].append({
                        "name": name,
                        "vectors": count,
                        "status": detail.get("status", "unknown"),
                    })
                    stats["total_vectors"] += count
    except Exception as e:
        stats["error"] = str(e)

    return stats


# ─── Metrics ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/metrics/summary")
async def metrics_summary():
    """Platform metrics summary."""
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "orchestrator_uptime_seconds": int((datetime.now(timezone.utc) - boot_time).total_seconds()),
        "services": {
            "total": len(SERVICE_REGISTRY),
            "healthy": sum(1 for h in health_cache.values() if h.status == HealthStatus.HEALTHY),
            "by_tier": {},
        },
    }

    for tier in ServiceTier:
        tier_services = [s for s in SERVICE_REGISTRY if s.tier == tier]
        tier_healthy = sum(
            1 for s in tier_services
            if s.id in health_cache and health_cache[s.id].status == HealthStatus.HEALTHY
        )
        metrics["services"]["by_tier"][tier.value] = {
            "total": len(tier_services),
            "healthy": tier_healthy,
        }

    # Pipeline stats
    if db_pool:
        try:
            pipeline_stats = await db_pool.fetchrow(
                """SELECT
                     COUNT(*) as total,
                     COUNT(*) FILTER (WHERE status = 'running') as running,
                     COUNT(*) FILTER (WHERE status = 'completed') as completed,
                     COUNT(*) FILTER (WHERE status = 'failed') as failed,
                     AVG(duration_seconds) FILTER (WHERE status = 'completed') as avg_duration
                   FROM pipeline_runs
                   WHERE started_at > NOW() - INTERVAL '24 hours'"""
            )
            metrics["pipelines_24h"] = dict(pipeline_stats) if pipeline_stats else {}
        except Exception:
            pass

    return metrics


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level=LOG_LEVEL.lower())
