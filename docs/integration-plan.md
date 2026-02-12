# ⚛ Omni Quantum Elite — Full Integration Plan

## Architecture Overview

The Omni Quantum Elite platform consists of **37 systems** organized in 5 tiers, running as Docker containers on a shared `omni-quantum-network`. System 37 (Master Orchestrator) is the capstone that monitors, health-checks, and coordinates all other systems.

---

## Tier Architecture & Boot Order

Services must start in dependency order. The platform uses a **tiered boot sequence**:

### Tier 0 — Foundation (Boot First)
These have zero dependencies. Everything else depends on them.

| System | Service | Port | Role |
|--------|---------|------|------|
| 1 | Backup Fortress | 8000 | Restic backup server |
| 2 | Cryptographic Fortress (Vault) | 8200 | Secrets management |
| 4 | Security Nexus (Authentik) | 9000 | Identity/SSO |
| 5 | Observatory (Prometheus) | 9090 | Metrics collection |
| 6 | Log Nexus (Loki) | 3100 | Log aggregation |
| 7 | Code Nexus (Gitea) | 3000 | Git hosting |
| 8 | Data Nexus (PostgreSQL) | 5432 | Primary database |
| 9 | Data Nexus (Redis) | 6379 | Cache/queue |
| 12 | Storage Nexus (MinIO) | 9000 | Object storage |

### Tier 1 — Core Services (Depend on Foundation)
| System | Service | Port | Depends On |
|--------|---------|------|------------|
| 3 | AI Gateway (LiteLLM) | 4000 | Vault, PostgreSQL |
| 10 | Communication Hub (Mattermost) | 8065 | PostgreSQL |
| 11 | Knowledge Base (Outline) | 3000 | PostgreSQL, Redis, MinIO |
| 34 | Gateway Sentinel Pro (Traefik) | 8080/8899 | — (CRITICAL tier) |

### Tier 2 — Intelligence Services (Depend on Core)
| System | Service | Port | Depends On |
|--------|---------|------|------------|
| 13 | Code Scorer | 8350 | — |
| 14 | Gate Engine | 8351 | — |
| 15 | Code Scorer v2 | 8350 | — |
| 16 | Gate Engine v2 | 8351 | — |
| 17 | Intent Verifier | 8352 | — |
| 18 | Context Compiler | 8325 | — |
| 19 | Tool Selector | 8326 | — |
| 20 | MCP Package Registry | 8327 | — |
| 21 | MCP Docs Server | 8328 | — |
| 22 | MCP Schema Validator | 8329 | — |
| 23 | MCP Pipeline Orchestrator | 8330 | — |
| 24 | Anti-Pattern Detector | 8331 | — |
| 25 | Spec Generator | 8332 | — |
| 26 | Prompt Decay Tracker | 8333 | — |
| 27 | Cross-Learning Engine | 8334 | — |

### Tier 3 — Enhanced Infrastructure
| System | Service | Port | Depends On |
|--------|---------|------|------------|
| 28 | IaC Lint | — | (build-time only) |
| 29 | Enhanced Monitoring | 8180-8183 | Prometheus |
| 30 | Enhanced Logging | 8184-8185 | Loki |
| 31 | Uptime Monitor (Uptime Kuma) | 3001 | — |
| 32 | Enhanced Backup | 8187-8188 | Backup, MinIO |
| 33 | Enhanced Secrets | 8189-8191 | Vault |
| 35 | CI/CD Pipelines (Woodpecker) | 8000/9000 | Gitea |
| 36 | Dev Environments (Coder) | 7080 | — |

### Tier 4 — Orchestration (Boot Last)
| System | Service | Port | Depends On |
|--------|---------|------|------------|
| 37 | Master Orchestrator | 9500 | All systems |
| 37 | Dashboard | 9501 | Orchestrator |
| 37 | Voice Bridge | 9502 | Orchestrator |
| 37 | Mattermost Bot | — | Orchestrator |
| 37 | Event Processor | — | Orchestrator |

---

## Integration Work Required

### Phase 1: Master Docker Compose (CRITICAL)
Create a single `docker-compose.master.yml` at the project root that:
- Defines the shared `omni-quantum-network` bridge network
- References all 37 system compose files using `include:` directives
- Sets environment variables for cross-service discovery
- Defines shared volumes (PostgreSQL data, Vault data, MinIO storage, etc.)
- Implements health checks and startup dependencies

```yaml
# docker-compose.master.yml (conceptual structure)
include:
  # Tier 0 - Foundation
  - path: systems/system-08-postgresql/docker-compose.yml  # External systems
  - path: systems/system-09-redis/docker-compose.yml
  # ... (external systems don't have compose files - they need creation)
  
  # Tier 2 - Intelligence Services  
  - path: services/code-scorer/docker-compose.yml
  - path: services/gate-engine/docker-compose.yml
  - path: services/context-compiler/docker-compose.yml
  # ... etc
  
  # Tier 3 - Enhanced Infrastructure
  - path: systems/system-29-pulse-command-pro/docker-compose.yml
  - path: systems/system-30-log-nexus-pro/docker-compose.yml
  # ... etc

  # Tier 4 - Orchestration
  - path: systems/system-37-omni-command/docker-compose.yml

networks:
  omni-quantum-network:
    driver: bridge
    name: omni-quantum-network
```

### Phase 2: Environment Configuration
Create a master `.env` file with all cross-service URLs:

```env
# Foundation
VAULT_URL=http://omni-vault:8200
POSTGRES_URL=postgresql://postgres:password@omni-postgres:5432
REDIS_URL=redis://omni-redis:6379
MINIO_URL=http://omni-minio:9000
PROMETHEUS_URL=http://omni-prometheus:9090
LOKI_URL=http://omni-loki:3100
GITEA_URL=http://omni-gitea:3000

# Core Services
LITELLM_URL=http://omni-litellm:4000
MATTERMOST_URL=http://omni-mattermost:8065
AUTHENTIK_URL=http://omni-authentik:9000
TRAEFIK_URL=http://omni-traefik:8080

# Intelligence Services
CODE_SCORER_URL=http://omni-code-scorer:8350
GATE_ENGINE_URL=http://omni-gate-engine:8351
INTENT_VERIFIER_URL=http://omni-intent-verifier:8352
CONTEXT_COMPILER_URL=http://omni-context-compiler:8325
TOOL_SELECTOR_URL=http://omni-tool-selector:8326
MCP_REGISTRY_URL=http://omni-mcp-registry:8327
MCP_DOCS_URL=http://omni-mcp-docs:8328
MCP_SCHEMA_URL=http://omni-mcp-schema:8329
MCP_PIPELINE_URL=http://omni-mcp-pipeline:8330
ANTI_PATTERNS_URL=http://omni-anti-patterns:8331
SPEC_GENERATOR_URL=http://omni-spec-generator:8332
PROMPT_DECAY_URL=http://omni-prompt-decay:8333
CROSS_LEARNING_URL=http://omni-cross-learning:8334

# Enhanced Infrastructure
THANOS_URL=http://omni-thanos-query:9091
UPTIME_KUMA_URL=http://omni-uptime-kuma:3001
BACKUP_ORCHESTRATOR_URL=http://omni-backup-orchestrator:8187
ROTATION_AGENT_URL=http://omni-secret-rotation:8189
WOODPECKER_URL=http://omni-woodpecker-server:8000
CODER_URL=http://omni-coder:7080

# Orchestrator
ORCHESTRATOR_URL=http://omni-orchestrator:9500
DASHBOARD_URL=http://omni-dashboard:9501
```

### Phase 3: Missing Foundation Compose Files
Systems 1-12 (except those already created) are **external services** (Vault, PostgreSQL, Redis, etc.) that currently have NO docker-compose files in the project. They need creation:

| System | Needs docker-compose.yml | Image |
|--------|--------------------------|-------|
| 1 | Backup (Restic) | `restic/rest-server` |
| 2 | Vault | `hashicorp/vault` |
| 3 | LiteLLM | `ghcr.io/berriai/litellm` |
| 4 | Authentik | `ghcr.io/goauthentik/server` |
| 5 | Prometheus | `prom/prometheus` |
| 6 | Loki | `grafana/loki` |
| 7 | Gitea | `gitea/gitea` |
| 8 | PostgreSQL | `postgres:16` |
| 9 | Redis | `redis:7` |
| 10 | Mattermost | `mattermost/mattermost-enterprise` |
| 11 | Outline | `outlinewiki/outline` |
| 12 | MinIO | `minio/minio` |

### Phase 4: Traefik Route Integration
System 34's `routes.yml` already defines reverse proxy routes for all services. Integration requires:
- Ensuring all container names match the Traefik route targets
- Configuring TLS certificates (Let's Encrypt via Traefik)
- Setting up authentication middleware (Authentik forward-auth)

### Phase 5: Verification Pipeline Integration
Wire the 4-tier verification pipeline into CI/CD:
- **verify-instant**: Runs on every commit (pyright + ruff, ~10s)
- **verify-fast**: Runs on every PR (unit tests, ~2min)  
- **verify-deep**: Runs on merge to main (integration tests, ~15min)
- **verify-nightly**: Runs daily (fuzzing + property-based testing, ~2hr)

The Woodpecker CI pipeline (System 35) already references these stages.

### Phase 6: Monitoring Stack Wiring
- All services expose `/metrics` (Prometheus format)
- System 29's anomaly detector scrapes these via Thanos
- System 29's SLA tracker monitors uptime targets
- System 29's capacity planner forecasts resource needs
- System 30's log correlator aggregates via Loki
- System 31's Uptime Kuma performs external health checks

### Phase 7: Security Hardening
- Falco runtime security monitoring (System 28)
- IaC linting on all Dockerfiles and compose files
- Vault auto-rotation of secrets (System 33)
- Threat model generation (security/threat-model/)
- Supply chain provenance (security/provenance/)

### Phase 8: Deployment Script
Create `deploy.sh` that:
1. Validates prerequisites (Docker, Docker Compose, min 16GB RAM)
2. Generates secure passwords/tokens for all services
3. Initializes Vault and seeds secrets
4. Boots Tier 0 and waits for health
5. Boots Tier 1 and waits for health
6. Boots Tier 2-3 in parallel
7. Boots Tier 4 (orchestrator)
8. Runs verify-instant on all services
9. Opens dashboard at https://localhost:9501

---

## Port Allocation Map (Complete)

```
Foundation:        3000-5432, 6379, 8000, 8200, 9000, 9090
Core:              4000, 8065, 8080, 8899
Intelligence:      8325-8334, 8350-8352
Enhanced Infra:    3001, 3100, 8180-8193, 9091
Orchestration:     9500-9502
CI/CD:             8000 (Woodpecker), 7080 (Coder)
Security:          8899 (Traefik API)
```

## Estimated Integration Effort

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1: Master Compose | 2-3 hours | 🔴 Critical |
| Phase 2: Environment Config | 30 min | 🔴 Critical |
| Phase 3: Foundation Compose Files | 3-4 hours | 🔴 Critical |
| Phase 4: Traefik Routes | 1-2 hours | 🟡 High |
| Phase 5: Verification Pipeline | 1 hour | 🟡 High |
| Phase 6: Monitoring Wiring | 2 hours | 🟡 High |
| Phase 7: Security Hardening | 2 hours | 🟢 Standard |
| Phase 8: Deployment Script | 2-3 hours | 🔴 Critical |

**Total estimated: ~15-18 hours of integration work**

---

## Current State Summary

✅ **COMPLETE**: 212 files, all 37 systems defined, service registry, health checks, CLI, dashboard, voice bridge, ChatOps bot, event processor, verification pipeline, CI/CD templates, security tooling, financial intelligence suite

🔧 **NEEDED**: Master compose orchestration, foundation service compose files (Systems 1-12), master .env, deployment automation script
