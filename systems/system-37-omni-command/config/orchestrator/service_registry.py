"""
Omni Quantum Elite — Service Registry
Filesystem-aligned registry for all registered systems.
"""

from dataclasses import dataclass, field
from enum import Enum


class Tier(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    STANDARD = "standard"


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
    compose_path: str
    container_name: str
    port: int
    tier: Tier
    healthcheck_url: str
    restart_policy: str = "unless-stopped"
    backup_schedule: str = ""
    description: str = ""
    env_key: str = ""
    health_path: str = "/health"
    health_type: HealthCheckType = HealthCheckType.HTTP_GET
    container: str = ""
    depends_on: list[int] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metrics_path: str = "/metrics"

    def __post_init__(self) -> None:
        if not self.container and self.container_name:
            self.container = self.container_name
        if not self.container_name and self.container:
            self.container_name = self.container
        if not self.backup_schedule:
            if self.tier == Tier.CRITICAL:
                self.backup_schedule = "0 */6 * * *"
            elif self.tier == Tier.HIGH:
                self.backup_schedule = "0 */12 * * *"
            else:
                self.backup_schedule = "0 3 * * *"


SERVICES: list[ServiceDef] = [
    ServiceDef(
        id=1,
        name="backup-fortress",
        codename="backup-fortress",
        compose_path="services/backup-fortress/docker-compose.yml",
        container_name="omni-backup-orchestrator",
        port=8000,
        tier=Tier.CRITICAL,
        healthcheck_url="http://omni-backup-orchestrator:8000/health",
        description="Restic-based backup orchestration",
        env_key="BACKUP_URL",
        health_path="/health",
        tags=["infrastructure", "data-protection"],
        depends_on=[12],
    ),
    ServiceDef(
        id=2,
        name="cryptographic-fortress",
        codename="cryptographic-fortress",
        compose_path="services/cryptographic-fortress/docker-compose.yml",
        container_name="omni-vault",
        port=8200,
        tier=Tier.CRITICAL,
        healthcheck_url="http://omni-vault:8200/v1/sys/health",
        description="Vault secrets management",
        env_key="VAULT_URL",
        health_path="/v1/sys/health",
        tags=["infrastructure", "security"],
    ),
    ServiceDef(
        id=3,
        name="ai-gateway",
        codename="ai-gateway",
        compose_path="services/ai-gateway/docker-compose.yml",
        container_name="omni-litellm",
        port=4000,
        tier=Tier.CRITICAL,
        healthcheck_url="http://omni-litellm:4000/health",
        description="LiteLLM gateway",
        env_key="LITELLM_URL",
        health_path="/health",
        tags=["ai", "gateway"],
        depends_on=[2, 8],
    ),
    ServiceDef(
        id=4,
        name="security-nexus",
        codename="security-nexus",
        compose_path="services/security-nexus/docker-compose.yml",
        container_name="omni-authentik",
        port=9000,
        tier=Tier.CRITICAL,
        healthcheck_url="http://omni-authentik:9000/-/health/ready/",
        description="Identity and SSO",
        env_key="AUTHENTIK_URL",
        health_path="/-/health/ready/",
        tags=["infrastructure", "security", "auth"],
        depends_on=[2],
    ),
    ServiceDef(
        id=5,
        name="observatory",
        codename="observatory",
        compose_path="services/observatory/docker-compose.yml",
        container_name="omni-prometheus",
        port=9090,
        tier=Tier.CRITICAL,
        healthcheck_url="http://omni-prometheus:9090/-/healthy",
        description="Metrics and dashboards",
        env_key="PROMETHEUS_URL",
        health_path="/-/healthy",
        tags=["infrastructure", "monitoring"],
    ),
    ServiceDef(
        id=6,
        name="log-nexus",
        codename="log-nexus",
        compose_path="services/log-nexus/docker-compose.yml",
        container_name="omni-loki",
        port=3100,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-loki:3100/ready",
        description="Centralized logging",
        env_key="LOKI_URL",
        health_path="/ready",
        tags=["infrastructure", "logging"],
        depends_on=[5],
    ),
    ServiceDef(
        id=7,
        name="code-fortress",
        codename="code-fortress",
        compose_path="services/code-fortress/docker-compose.yml",
        container_name="omni-gitea",
        port=3000,
        tier=Tier.CRITICAL,
        healthcheck_url="http://omni-gitea:3000/api/v1/version",
        description="Git hosting",
        env_key="GITEA_URL",
        health_path="/api/v1/version",
        tags=["development", "git"],
    ),
    ServiceDef(
        id=8,
        name="neural-network",
        codename="neural-network",
        compose_path="services/neural-network/docker-compose.yml",
        container_name="omni-ollama",
        port=11434,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-ollama:11434/api/tags",
        description="Local LLM inference",
        env_key="OLLAMA_URL",
        health_path="/api/tags",
        tags=["ai", "inference"],
    ),
    ServiceDef(
        id=9,
        name="workflow-engine",
        codename="workflow-engine",
        compose_path="services/workflow-engine/docker-compose.yml",
        container_name="omni-n8n",
        port=5678,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-n8n:5678/healthz",
        description="Workflow automation",
        env_key="N8N_URL",
        health_path="/healthz",
        tags=["automation", "workflows"],
    ),
    ServiceDef(
        id=10,
        name="communication-hub",
        codename="communication-hub",
        compose_path="services/communication-hub/docker-compose.yml",
        container_name="omni-mattermost",
        port=8065,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-mattermost:8065/api/v4/system/ping",
        description="ChatOps and communication",
        env_key="MATTERMOST_URL",
        health_path="/api/v4/system/ping",
        tags=["communication", "chatops"],
    ),
    ServiceDef(
        id=11,
        name="vector-memory",
        codename="vector-memory",
        compose_path="services/vector-memory/docker-compose.yml",
        container_name="omni-qdrant",
        port=6333,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-qdrant:6333/healthz",
        description="Vector database",
        env_key="QDRANT_URL",
        health_path="/healthz",
        tags=["ai", "database", "embeddings"],
    ),
    ServiceDef(
        id=12,
        name="object-store",
        codename="object-store",
        compose_path="services/object-store/docker-compose.yml",
        container_name="omni-minio",
        port=9000,
        tier=Tier.CRITICAL,
        healthcheck_url="http://omni-minio:9000/minio/health/live",
        description="S3-compatible object storage",
        env_key="MINIO_URL",
        health_path="/minio/health/live",
        tags=["infrastructure", "storage"],
    ),
    ServiceDef(
        id=13,
        name="ai-observability",
        codename="ai-observability",
        compose_path="services/ai-observability/docker-compose.yml",
        container_name="omni-langfuse",
        port=3000,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-langfuse:3000/api/public/health",
        description="LLM observability and tracing",
        env_key="LANGFUSE_URL",
        health_path="/api/public/health",
        tags=["ai", "observability"],
        depends_on=[3],
    ),
    ServiceDef(
        id=14,
        name="project-command",
        codename="project-command",
        compose_path="services/project-command/docker-compose.yml",
        container_name="notion-workspace",
        port=443,
        tier=Tier.STANDARD,
        healthcheck_url="https://notion.so/",
        description="Notion-backed project command",
        env_key="PLANE_URL",
        health_path="/",
        tags=["management", "projects"],
    ),
    ServiceDef(
        id=15,
        name="integration-hub",
        codename="integration-hub",
        compose_path="services/integration-hub/docker-compose.yml",
        container_name="omni-nango",
        port=3003,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-nango:3003/health",
        description="Integration platform",
        env_key="NANGO_URL",
        health_path="/health",
        tags=["integration", "apis"],
    ),
    ServiceDef(
        id=16,
        name="ai-coder-alpha",
        codename="ai-coder-alpha",
        compose_path="services/ai-coder-alpha/docker-compose.yml",
        container_name="omni-openhands-core",
        port=3000,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-openhands-core:3000/health",
        description="Autonomous AI software engineer",
        env_key="OPENHANDS_URL",
        health_path="/health",
        tags=["ai", "coding", "agent"],
        depends_on=[3, 7],
    ),
    ServiceDef(
        id=17,
        name="ai-coder-beta",
        codename="ai-coder-beta",
        compose_path="services/ai-coder-beta/docker-compose.yml",
        container_name="omni-swe-agent-core",
        port=8000,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-swe-agent-core:8000/health",
        description="AI bug fixer and code generator",
        env_key="SWEAGENT_URL",
        health_path="/health",
        tags=["ai", "coding", "agent"],
        depends_on=[3, 7],
    ),
    ServiceDef(
        id=18,
        name="deploy-engine",
        codename="deploy-engine",
        compose_path="services/deploy-engine/docker-compose.yml",
        container_name="omni-coolify",
        port=8000,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-coolify:8000/api/health",
        description="Deployment engine",
        env_key="COOLIFY_URL",
        health_path="/api/health",
        tags=["deployment", "paas"],
    ),
    ServiceDef(
        id=19,
        name="flow-builder",
        codename="flow-builder",
        compose_path="services/flow-builder/docker-compose.yml",
        container_name="omni-flowise",
        port=3000,
        tier=Tier.STANDARD,
        healthcheck_url="http://omni-flowise:3000/api/v1/ping",
        description="Visual AI workflow builder",
        env_key="FLOWISE_URL",
        health_path="/api/v1/ping",
        tags=["ai", "workflows", "visual"],
        depends_on=[3],
    ),
    ServiceDef(
        id=20,
        name="knowledge-base",
        codename="knowledge-base",
        compose_path="services/knowledge-base/docker-compose.yml",
        container_name="notion-workspace",
        port=443,
        tier=Tier.STANDARD,
        healthcheck_url="https://notion.so/",
        description="Notion-backed knowledge base",
        env_key="WIKIJS_URL",
        health_path="/",
        tags=["documentation", "knowledge"],
    ),
    ServiceDef(
        id=21,
        name="analytics-engine",
        codename="analytics-engine",
        compose_path="services/analytics-engine/docker-compose.yml",
        container_name="omni-superset",
        port=8088,
        tier=Tier.STANDARD,
        healthcheck_url="http://omni-superset:8088/health",
        description="Analytics dashboards",
        env_key="SUPERSET_URL",
        health_path="/health",
        tags=["analytics", "data"],
    ),
    ServiceDef(
        id=22,
        name="schedule-manager",
        codename="schedule-manager",
        compose_path="services/schedule-manager/docker-compose.yml",
        container_name="omni-calcom",
        port=3000,
        tier=Tier.STANDARD,
        healthcheck_url="http://omni-calcom:3000/api/health",
        description="Scheduling system",
        env_key="CALCOM_URL",
        health_path="/api/health",
        tags=["scheduling", "calendar"],
    ),
    ServiceDef(
        id=23,
        name="crm-hub",
        codename="crm-hub",
        compose_path="services/crm-hub/docker-compose.yml",
        container_name="notion-workspace",
        port=443,
        tier=Tier.STANDARD,
        healthcheck_url="https://notion.so/",
        description="Notion-backed CRM",
        env_key="TWENTY_URL",
        health_path="/",
        tags=["crm", "business"],
    ),
    ServiceDef(
        id=24,
        name="invoice-manager",
        codename="invoice-manager",
        compose_path="services/invoice-manager/docker-compose.yml",
        container_name="omni-crater",
        port=80,
        tier=Tier.STANDARD,
        healthcheck_url="http://omni-crater:80/api/health",
        description="Invoicing",
        env_key="CRATER_URL",
        health_path="/api/health",
        tags=["invoicing", "business"],
    ),
    ServiceDef(
        id=25,
        name="security-shield",
        codename="security-shield",
        compose_path="services/security-shield/docker-compose.yml",
        container_name="omni-crowdsec",
        port=8080,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-crowdsec:8080/v1/heartbeat",
        description="Intrusion prevention",
        env_key="CROWDSEC_URL",
        health_path="/v1/heartbeat",
        tags=["security", "firewall"],
    ),
    ServiceDef(
        id=26,
        name="container-manager",
        codename="container-manager",
        compose_path="services/container-manager/docker-compose.yml",
        container_name="omni-portainer",
        port=9000,
        tier=Tier.STANDARD,
        healthcheck_url="http://omni-portainer:9000/api/system/status",
        description="Container management UI",
        env_key="PORTAINER_URL",
        health_path="/api/system/status",
        tags=["infrastructure", "containers"],
    ),
    ServiceDef(
        id=27,
        name="token-infinity",
        codename="token-infinity",
        compose_path="services/token-infinity/docker-compose.yml",
        container_name="omni-context-manager",
        port=9600,
        tier=Tier.CRITICAL,
        healthcheck_url="http://omni-context-manager:9600/health",
        description="Token routing and context management",
        env_key="TOKEN_INFINITY_URL",
        health_path="/health",
        tags=["ai", "tokens", "routing"],
        depends_on=[3, 8],
    ),
    ServiceDef(
        id=28,
        name="omi-bridge",
        codename="omi-bridge",
        compose_path="services/omi-bridge/docker-compose.yml",
        container_name="omni-omi-bridge",
        port=9700,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-omi-bridge:9700/health",
        description="Wearable bridge",
        env_key="OMI_BRIDGE_URL",
        health_path="/health",
        tags=["ai", "voice", "wearable"],
        depends_on=[3],
    ),
    ServiceDef(
        id=29,
        name="system-29-pulse-command-pro",
        codename="system-29-pulse-command-pro",
        compose_path="systems/system-29-pulse-command-pro/docker-compose.yml",
        container_name="omni-thanos-query",
        port=9091,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-thanos-query:9091/-/healthy",
        description="Enhanced monitoring stack",
        env_key="THANOS_URL",
        health_path="/-/healthy",
        tags=["infrastructure", "monitoring", "enhanced"],
        depends_on=[5],
    ),
    ServiceDef(
        id=30,
        name="system-30-log-nexus-pro",
        codename="system-30-log-nexus-pro",
        compose_path="systems/system-30-log-nexus-pro/docker-compose.yml",
        container_name="omni-log-pattern-detector",
        port=8184,
        tier=Tier.STANDARD,
        healthcheck_url="http://omni-log-pattern-detector:8184/health",
        description="Log pattern and correlation",
        env_key="LOG_PATTERN_DETECTOR_URL",
        health_path="/health",
        tags=["infrastructure", "logging", "enhanced"],
        depends_on=[6],
    ),
    ServiceDef(
        id=31,
        name="system-31-guardian-eye",
        codename="system-31-guardian-eye",
        compose_path="systems/system-31-guardian-eye/docker-compose.yml",
        container_name="omni-uptime-kuma",
        port=3001,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-uptime-kuma:3001/api/health",
        description="Uptime monitoring",
        env_key="UPTIME_KUMA_URL",
        health_path="/api/health",
        tags=["infrastructure", "uptime"],
    ),
    ServiceDef(
        id=32,
        name="system-32-backup-fortress-pro",
        codename="system-32-backup-fortress-pro",
        compose_path="systems/system-32-backup-fortress-pro/docker-compose.yml",
        container_name="omni-backup-verifier",
        port=8188,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-backup-verifier:8188/health",
        description="Backup verification and orchestration",
        env_key="BACKUP_VERIFIER_URL",
        health_path="/health",
        tags=["infrastructure", "backup", "enhanced"],
        depends_on=[1, 12],
    ),
    ServiceDef(
        id=33,
        name="system-33-crypto-fortress-pro",
        codename="system-33-crypto-fortress-pro",
        compose_path="systems/system-33-crypto-fortress-pro/docker-compose.yml",
        container_name="omni-secret-rotation-agent",
        port=8189,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-secret-rotation-agent:8189/health",
        description="Secrets rotation and PKI",
        env_key="ROTATION_AGENT_URL",
        health_path="/health",
        tags=["infrastructure", "security", "enhanced"],
        depends_on=[2],
    ),
    ServiceDef(
        id=34,
        name="system-34-gateway-sentinel-pro",
        codename="system-34-gateway-sentinel-pro",
        compose_path="systems/system-34-gateway-sentinel-pro/docker-compose.yml",
        container_name="omni-traefik",
        port=8080,
        tier=Tier.CRITICAL,
        healthcheck_url="http://omni-traefik:8080/ping",
        description="Traefik reverse proxy",
        env_key="TRAEFIK_URL",
        health_path="/ping",
        tags=["infrastructure", "proxy", "enhanced"],
    ),
    ServiceDef(
        id=35,
        name="system-35-build-forge",
        codename="system-35-build-forge",
        compose_path="systems/system-35-build-forge/docker-compose.yml",
        container_name="omni-woodpecker-server",
        port=8000,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-woodpecker-server:8000/healthz",
        description="CI/CD pipelines",
        env_key="WOODPECKER_URL",
        health_path="/healthz",
        tags=["development", "cicd"],
        depends_on=[7],
    ),
    ServiceDef(
        id=36,
        name="system-36-code-forge",
        codename="system-36-code-forge",
        compose_path="systems/system-36-code-forge/docker-compose.yml",
        container_name="omni-coder",
        port=7080,
        tier=Tier.STANDARD,
        healthcheck_url="http://omni-coder:7080/healthz",
        description="Development workspaces",
        env_key="CODER_URL",
        health_path="/healthz",
        tags=["development", "workspaces"],
    ),
    ServiceDef(
        id=37,
        name="temporal-orchestrator",
        codename="temporal-orchestrator",
        compose_path="services/temporal-orchestrator/docker-compose.yml",
        container_name="omni-temporal-orchestrator",
        port=9650,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-temporal-orchestrator:9650/health",
        description="Durable workflow orchestration control plane",
        env_key="TEMPORAL_ORCHESTRATOR_URL",
        health_path="/health",
        tags=["orchestration", "workflows", "durability"],
        depends_on=[9],
    ),
    ServiceDef(
        id=38,
        name="observability-otel",
        codename="observability-otel",
        compose_path="services/observability-otel/docker-compose.yml",
        container_name="omni-observability-otel",
        port=9651,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-observability-otel:9651/health",
        description="OpenTelemetry instrumentation and collector control plane",
        env_key="OBSERVABILITY_OTEL_URL",
        health_path="/health",
        tags=["observability", "telemetry", "tracing"],
        depends_on=[5],
    ),
    ServiceDef(
        id=39,
        name="policy-engine",
        codename="policy-engine",
        compose_path="services/policy-engine/docker-compose.yml",
        container_name="omni-policy-engine",
        port=9652,
        tier=Tier.CRITICAL,
        healthcheck_url="http://omni-policy-engine:9652/health",
        description="Centralized policy decisions with OPA/Rego",
        env_key="POLICY_ENGINE_URL",
        health_path="/health",
        tags=["security", "policy", "governance"],
        depends_on=[2, 4],
    ),
    ServiceDef(
        id=40,
        name="attestation-hub",
        codename="attestation-hub",
        compose_path="services/attestation-hub/docker-compose.yml",
        container_name="omni-attestation-hub",
        port=9653,
        tier=Tier.HIGH,
        healthcheck_url="http://omni-attestation-hub:9653/health",
        description="Supply chain provenance and SBOM attestation service",
        env_key="ATTESTATION_HUB_URL",
        health_path="/health",
        tags=["security", "supply-chain", "attestations"],
        depends_on=[35, 39],
    ),
]


SERVICE_BY_ID: dict[int, ServiceDef] = {s.id: s for s in SERVICES}
SERVICE_BY_CODENAME: dict[str, ServiceDef] = {s.codename: s for s in SERVICES}


def get_services_by_tier(tier: Tier) -> list[ServiceDef]:
    return [s for s in SERVICES if s.tier == tier]


def get_services_by_tag(tag: str) -> list[ServiceDef]:
    return [s for s in SERVICES if tag in s.tags]


def get_dependency_order() -> list[ServiceDef]:
    visited: set[int] = set()
    order: list[ServiceDef] = []

    def visit(sid: int) -> None:
        if sid in visited:
            return
        visited.add(sid)
        svc = SERVICE_BY_ID.get(sid)
        if svc:
            for dep in svc.depends_on:
                visit(dep)
            order.append(svc)

    for svc in SERVICES:
        visit(svc.id)
    return order


def get_invalid_compose_paths() -> list[str]:
    import os

    return [s.compose_path for s in SERVICES if not os.path.exists(s.compose_path)]
