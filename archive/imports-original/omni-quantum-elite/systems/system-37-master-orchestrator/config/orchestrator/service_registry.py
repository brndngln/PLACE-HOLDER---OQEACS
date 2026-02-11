"""
Omni Quantum Elite — Service Registry
Complete registry of all 36 systems with health check endpoints,
dependencies, tiers, and metadata.
"""

from dataclasses import dataclass, field
from enum import Enum


class Tier(str, Enum):
    CRITICAL = "critical"   # Must be running — platform cannot function without
    HIGH = "high"           # Important — degraded experience if down
    STANDARD = "standard"   # Useful — platform works without but with reduced features


class HealthCheckType(str, Enum):
    HTTP_GET = "http_get"
    HTTP_POST = "http_post"
    TCP = "tcp"
    DOCKER = "docker"


@dataclass
class ServiceDef:
    id: int
    name: str
    codename: str
    description: str
    tier: Tier
    env_key: str                              # environment variable holding URL
    health_path: str = "/health"
    health_type: HealthCheckType = HealthCheckType.HTTP_GET
    port: int = 0
    container: str = ""
    depends_on: list[int] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metrics_path: str = "/metrics"


# =============================================================================
# COMPLETE REGISTRY — All 36 Systems
# =============================================================================
SERVICES: list[ServiceDef] = [
    # ---- Foundation Layer ----
    ServiceDef(
        id=1, name="Backup Fortress", codename="backup",
        description="Restic-based backup with S3 storage",
        tier=Tier.CRITICAL, env_key="BACKUP_URL",
        health_path="/", port=8000,
        container="omni-restic-server",
        tags=["infrastructure", "data-protection"],
    ),
    ServiceDef(
        id=2, name="Cryptographic Fortress", codename="vault",
        description="HashiCorp Vault — secrets management",
        tier=Tier.CRITICAL, env_key="VAULT_URL",
        health_path="/v1/sys/health", port=8200,
        container="omni-vault",
        tags=["infrastructure", "security"],
    ),
    ServiceDef(
        id=3, name="AI Gateway", codename="litellm",
        description="LiteLLM — unified LLM proxy and load balancer",
        tier=Tier.CRITICAL, env_key="LITELLM_URL",
        health_path="/health", port=4000,
        container="omni-litellm",
        depends_on=[2, 8],
        tags=["ai", "gateway"],
    ),
    ServiceDef(
        id=4, name="Security Nexus", codename="authentik",
        description="Authentik — identity provider and SSO",
        tier=Tier.CRITICAL, env_key="AUTHENTIK_URL",
        health_path="/-/health/ready/", port=9443,
        container="omni-authentik",
        tags=["infrastructure", "security", "auth"],
    ),
    ServiceDef(
        id=5, name="Observatory", codename="prometheus",
        description="Prometheus + Grafana — metrics and dashboards",
        tier=Tier.CRITICAL, env_key="PROMETHEUS_URL",
        health_path="/-/healthy", port=9090,
        container="omni-prometheus",
        tags=["infrastructure", "monitoring"],
    ),
    ServiceDef(
        id=6, name="Log Nexus", codename="loki",
        description="Loki + Promtail — centralized logging",
        tier=Tier.HIGH, env_key="LOKI_URL",
        health_path="/ready", port=3100,
        container="omni-loki",
        tags=["infrastructure", "logging"],
    ),

    # ---- Development Layer ----
    ServiceDef(
        id=7, name="Code Fortress", codename="gitea",
        description="Gitea — self-hosted Git with CI/CD",
        tier=Tier.CRITICAL, env_key="GITEA_URL",
        health_path="/api/v1/version", port=3000,
        container="omni-gitea",
        tags=["development", "git"],
    ),
    ServiceDef(
        id=8, name="Neural Network", codename="ollama",
        description="Ollama — local LLM inference engine",
        tier=Tier.HIGH, env_key="OLLAMA_URL",
        health_path="/api/tags", port=11434,
        container="omni-ollama",
        tags=["ai", "inference"],
    ),
    ServiceDef(
        id=9, name="Workflow Engine", codename="n8n",
        description="n8n — workflow automation platform",
        tier=Tier.HIGH, env_key="N8N_URL",
        health_path="/healthz", port=5678,
        container="omni-n8n",
        tags=["automation", "workflows"],
    ),
    ServiceDef(
        id=10, name="Communication Hub", codename="mattermost",
        description="Mattermost — team communication and ChatOps",
        tier=Tier.HIGH, env_key="MATTERMOST_URL",
        health_path="/api/v4/system/ping", port=8065,
        container="omni-mattermost",
        tags=["communication", "chatops"],
    ),
    ServiceDef(
        id=11, name="Vector Memory", codename="qdrant",
        description="Qdrant — vector database for embeddings",
        tier=Tier.HIGH, env_key="QDRANT_URL",
        health_path="/healthz", port=6333,
        container="omni-qdrant",
        tags=["ai", "database", "embeddings"],
    ),
    ServiceDef(
        id=12, name="Object Store", codename="minio",
        description="MinIO — S3-compatible object storage",
        tier=Tier.CRITICAL, env_key="MINIO_URL",
        health_path="/minio/health/live", port=9000,
        container="omni-minio",
        tags=["infrastructure", "storage"],
    ),
    ServiceDef(
        id=13, name="AI Observability", codename="langfuse",
        description="Langfuse — LLM observability and tracing",
        tier=Tier.HIGH, env_key="LANGFUSE_URL",
        health_path="/api/public/health", port=3000,
        container="omni-langfuse",
        depends_on=[3],
        tags=["ai", "observability"],
    ),
    ServiceDef(
        id=14, name="Project Command", codename="plane",
        description="Plane — project management and issue tracking",
        tier=Tier.STANDARD, env_key="PLANE_URL",
        health_path="/", port=3000,
        container="omni-plane-web",
        tags=["management", "projects"],
    ),
    ServiceDef(
        id=15, name="Integration Hub", codename="nango",
        description="Nango — unified API integration platform",
        tier=Tier.HIGH, env_key="NANGO_URL",
        health_path="/health", port=3003,
        container="omni-nango",
        tags=["integration", "apis"],
    ),
    ServiceDef(
        id=16, name="AI Coder Alpha", codename="openhands",
        description="OpenHands — autonomous AI software engineer",
        tier=Tier.HIGH, env_key="OPENHANDS_URL",
        health_path="/api/health", port=3000,
        container="omni-openhands",
        depends_on=[3, 7],
        tags=["ai", "coding", "agent"],
    ),
    ServiceDef(
        id=17, name="AI Coder Beta", codename="swe-agent",
        description="SWE-Agent — AI bug fixer and code generator",
        tier=Tier.HIGH, env_key="SWEAGENT_URL",
        health_path="/health", port=8000,
        container="omni-swe-agent",
        depends_on=[3, 7],
        tags=["ai", "coding", "agent"],
    ),
    ServiceDef(
        id=18, name="Deploy Engine", codename="coolify",
        description="Coolify — self-hosted PaaS for deployments",
        tier=Tier.HIGH, env_key="COOLIFY_URL",
        health_path="/api/v1/healthcheck", port=8000,
        container="omni-coolify",
        tags=["deployment", "paas"],
    ),
    ServiceDef(
        id=19, name="Flow Builder", codename="flowise",
        description="Flowise — visual AI workflow builder",
        tier=Tier.STANDARD, env_key="FLOWISE_URL",
        health_path="/api/v1/ping", port=3000,
        container="omni-flowise",
        depends_on=[3],
        tags=["ai", "workflows", "visual"],
    ),
    ServiceDef(
        id=20, name="Knowledge Base", codename="wikijs",
        description="Wiki.js — documentation and knowledge management",
        tier=Tier.STANDARD, env_key="WIKIJS_URL",
        health_path="/healthz", port=3000,
        container="omni-wikijs",
        tags=["documentation", "knowledge"],
    ),
    ServiceDef(
        id=21, name="Analytics Engine", codename="superset",
        description="Apache Superset — data exploration and dashboards",
        tier=Tier.STANDARD, env_key="SUPERSET_URL",
        health_path="/health", port=8088,
        container="omni-superset",
        tags=["analytics", "data"],
    ),
    ServiceDef(
        id=22, name="Schedule Manager", codename="calcom",
        description="Cal.com — scheduling and calendar management",
        tier=Tier.STANDARD, env_key="CALCOM_URL",
        health_path="/api/health", port=3000,
        container="omni-calcom",
        tags=["scheduling", "calendar"],
    ),
    ServiceDef(
        id=23, name="CRM Hub", codename="twenty",
        description="Twenty CRM — customer relationship management",
        tier=Tier.STANDARD, env_key="TWENTY_URL",
        health_path="/healthz", port=3000,
        container="omni-twenty",
        tags=["crm", "business"],
    ),
    ServiceDef(
        id=24, name="Invoice Manager", codename="crater",
        description="Crater — invoicing and expense management",
        tier=Tier.STANDARD, env_key="CRATER_URL",
        health_path="/", port=80,
        container="omni-crater",
        tags=["invoicing", "business"],
    ),
    ServiceDef(
        id=25, name="Security Shield", codename="crowdsec",
        description="CrowdSec — collaborative intrusion prevention",
        tier=Tier.HIGH, env_key="CROWDSEC_URL",
        health_path="/v1/heartbeat", port=8080,
        container="omni-crowdsec",
        tags=["security", "firewall"],
    ),
    ServiceDef(
        id=26, name="Container Manager", codename="portainer",
        description="Portainer — Docker container management UI",
        tier=Tier.STANDARD, env_key="PORTAINER_URL",
        health_path="/api/system/status", port=9000,
        container="omni-portainer",
        tags=["infrastructure", "containers"],
    ),
    ServiceDef(
        id=27, name="Token Infinity", codename="token-infinity",
        description="Unlimited token routing across free LLM providers",
        tier=Tier.CRITICAL, env_key="TOKEN_INFINITY_URL",
        health_path="/health", port=9600,
        container="omni-token-infinity",
        depends_on=[3, 8],
        tags=["ai", "tokens", "routing"],
    ),
    ServiceDef(
        id=28, name="Omi Wearable Bridge", codename="omi-bridge",
        description="Voice-first AI assistant via Omi wearable",
        tier=Tier.HIGH, env_key="OMI_BRIDGE_URL",
        health_path="/health", port=9700,
        container="omni-omi-bridge",
        depends_on=[3],
        tags=["ai", "voice", "wearable"],
    ),

    # ---- Enhanced Infrastructure (Systems 29-36) ----
    ServiceDef(
        id=29, name="Pulse Command Pro", codename="enhanced-monitoring",
        description="Thanos + Anomaly Detection + SLA Tracking + Capacity Planning",
        tier=Tier.HIGH, env_key="THANOS_URL",
        health_path="/api/v1/status/runtimeinfo", port=9091,
        container="omni-thanos-query",
        depends_on=[5],
        tags=["infrastructure", "monitoring", "enhanced"],
    ),
    ServiceDef(
        id=30, name="Log Nexus Pro", codename="enhanced-logging",
        description="Log pattern detection + trace correlation",
        tier=Tier.STANDARD, env_key="LOG_PATTERN_DETECTOR_URL",
        health_path="/health", port=8184,
        container="omni-log-pattern-detector",
        depends_on=[6],
        tags=["infrastructure", "logging", "enhanced"],
    ),
    ServiceDef(
        id=31, name="Guardian Eye", codename="uptime-monitor",
        description="Uptime Kuma — health checks and status page",
        tier=Tier.HIGH, env_key="UPTIME_KUMA_URL",
        health_path="/api/status-page/heartbeat/omni-quantum", port=3001,
        container="omni-uptime-kuma",
        tags=["infrastructure", "uptime"],
    ),
    ServiceDef(
        id=32, name="Backup Fortress Pro", codename="enhanced-backup",
        description="Automated backup orchestration + verification",
        tier=Tier.HIGH, env_key="BACKUP_ORCHESTRATOR_URL",
        health_path="/health", port=8187,
        container="omni-backup-orchestrator",
        depends_on=[1, 12],
        tags=["infrastructure", "backup", "enhanced"],
    ),
    ServiceDef(
        id=33, name="Cryptographic Fortress Pro", codename="enhanced-secrets",
        description="Auto-rotation + PKI + audit for secrets",
        tier=Tier.HIGH, env_key="ROTATION_AGENT_URL",
        health_path="/health", port=8189,
        container="omni-secret-rotation-agent",
        depends_on=[2],
        tags=["infrastructure", "security", "enhanced"],
    ),
    ServiceDef(
        id=34, name="Gateway Sentinel Pro", codename="enhanced-proxy",
        description="Traefik — advanced reverse proxy with mTLS and rate limiting",
        tier=Tier.CRITICAL, env_key="TRAEFIK_URL",
        health_path="/api/overview", port=8080,
        container="omni-traefik",
        tags=["infrastructure", "proxy", "enhanced"],
    ),
    ServiceDef(
        id=35, name="Build Forge", codename="cicd-pipelines",
        description="Woodpecker CI — automated build, test, deploy pipelines",
        tier=Tier.HIGH, env_key="WOODPECKER_URL",
        health_path="/healthz", port=8000,
        container="omni-woodpecker-server",
        depends_on=[7],
        tags=["development", "cicd"],
    ),
    ServiceDef(
        id=36, name="Code Forge", codename="dev-environments",
        description="Coder — browser-based development workspaces",
        tier=Tier.STANDARD, env_key="CODER_URL",
        health_path="/api/v2/buildinfo", port=7080,
        container="omni-coder",
        tags=["development", "workspaces"],
    ),
]


# Lookup helpers
SERVICE_BY_ID: dict[int, ServiceDef] = {s.id: s for s in SERVICES}
SERVICE_BY_CODENAME: dict[str, ServiceDef] = {s.codename: s for s in SERVICES}


def get_services_by_tier(tier: Tier) -> list[ServiceDef]:
    return [s for s in SERVICES if s.tier == tier]


def get_services_by_tag(tag: str) -> list[ServiceDef]:
    return [s for s in SERVICES if tag in s.tags]


def get_dependency_order() -> list[ServiceDef]:
    """Topological sort of services by dependency."""
    visited: set[int] = set()
    order: list[ServiceDef] = []

    def visit(sid: int):
        if sid in visited:
            return
        visited.add(sid)
        svc = SERVICE_BY_ID.get(sid)
        if svc:
            for dep in svc.depends_on:
                visit(dep)
            order.append(svc)

    for s in SERVICES:
        visit(s.id)
    return order
