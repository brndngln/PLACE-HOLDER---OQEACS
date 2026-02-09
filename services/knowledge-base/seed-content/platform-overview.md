# Omni Quantum Elite AI Coding System — Platform Architecture Overview

## Executive Summary

The Omni Quantum Elite AI Coding System is a self-hosted, GPU-accelerated platform comprising **37 integrated systems** organized across an **8-stage AI coding pipeline**. The platform delivers end-to-end AI-assisted software development, from code generation through deployment, with built-in observability, security, and knowledge management.

All services run on a unified Docker Compose stack connected via the `omni-quantum-network` bridge. Container naming follows the `omni-` prefix convention with structured labels for tier classification and component identification.

---

## 8-Stage AI Coding Pipeline

```
┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Stage 1  │──▶│ Stage 2  │──▶│ Stage 3  │──▶│ Stage 4  │
│ Ingest   │   │ Enrich   │   │ Generate │   │ Validate │
└─────────┘   └──────────┘   └──────────┘   └──────────┘
      │              │              │              │
      ▼              ▼              ▼              ▼
┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Stage 5  │──▶│ Stage 6  │──▶│ Stage 7  │──▶│ Stage 8  │
│ Test     │   │ Deploy   │   │ Monitor  │   │ Learn    │
└─────────┘   └──────────┘   └──────────┘   └──────────┘
```

### Stage 1 — Ingest
Captures requirements, code context, and documentation from external sources.
- **Knowledge Ingestor** (System 18): Watches Git repos, Confluence, Slack; extracts text, chunks, embeds via Qdrant.
- **Freshness Monitor** (System 19): Tracks document staleness, triggers re-ingestion when sources change.
- **Semantic Cache** (System 16): Deduplicates embedding lookups using Qdrant-backed similarity search.

### Stage 2 — Enrich
Augments raw context with design pattern knowledge and historical data.
- **Neo4j GraphRAG** (System 67): 54-pattern knowledge graph with category, language, codebase, and anti-pattern relationships.
- **Knowledge Base / Wiki.js** (System 20): Human-curated documentation, runbooks, and templates.
- **Vector Memory** (System 15): Long-term conversation and code embedding storage via Qdrant collections.

### Stage 3 — Generate
Produces code, documentation, and architecture recommendations.
- **LiteLLM Proxy** (System 4): Unified gateway to 200+ LLM providers. Routes, rate-limits, and caches completions.
- **Ollama** (System 3): Local GPU-accelerated model serving (CodeLlama, DeepSeek, StarCoder).
- **AI Coder Alpha** (System 5 — OpenHands): Autonomous coding agent with terminal, browser, and file access.
- **AI Coder Beta** (System 6 — SWE-Agent): Research-grade coding agent for complex bug fixes and refactors.

### Stage 4 — Validate
Reviews, lints, and verifies generated code before merge.
- **Code Forge / Woodpecker CI** (System 8): CI/CD pipeline with parallel test execution and artifact publishing.
- **Security Shield** (System 10): SAST/DAST scanning, dependency auditing, container image scanning.
- **Code Fortress / SonarQube** (System 9): Continuous code quality analysis with quality gates.

### Stage 5 — Test
Executes comprehensive test suites and performance benchmarks.
- **Build Forge** (System 7 — Coder): Cloud development environments for test execution and debugging.
- **Workflow Engine / n8n** (System 12): Orchestrates multi-step test-and-deploy workflows.

### Stage 6 — Deploy
Manages container builds, registry storage, and deployment.
- **Container Manager** (System 11 — Portainer): Container lifecycle management, stack deployment.
- **Gateway Sentinel / Traefik** (System 14): Reverse proxy with automatic TLS, routing, and rate limiting.
- **Backup Fortress / Duplicati** (System 1): Automated backups of volumes, databases, and configuration.

### Stage 7 — Monitor
Provides full-stack observability across all services.
- **Observatory / Grafana** (System 13): Dashboards, alerting, and visualization for all telemetry data.
- **Log Nexus** (System 35): Centralized log aggregation (Loki), structured JSON ingestion.
- **AI Observability / Langfuse** (System 17): LLM-specific tracing, token usage, latency, and quality scoring.

### Stage 8 — Learn
Feeds outcomes back into the knowledge layer for continuous improvement.
- **Token Infinity** (System 66): Infinite-context retrieval-augmented generation. Queries Neo4j, Qdrant, and Wiki.js to build optimal LLM prompts.
- **Neural Network** (System 36): Internal communication (Rocket.Chat) with bot integrations.
- **Integration Hub** (System 37): Webhook-based event routing between systems.

---

## System Inventory (37 Systems)

| # | System | Container | Port | Tier |
|---|--------|-----------|------|------|
| 1 | Backup Fortress | omni-duplicati | 8200 | Foundation |
| 2 | Security Nexus / Vault | omni-vault | 8200 | Foundation |
| 3 | Ollama | omni-ollama | 11434 | AI |
| 4 | LiteLLM Proxy | omni-litellm | 4000 | AI |
| 5 | AI Coder Alpha (OpenHands) | omni-openhands | 3100 | AI |
| 6 | AI Coder Beta (SWE-Agent) | omni-swe-agent | 3200 | AI |
| 7 | Build Forge (Coder) | omni-coder | 7080 | Development |
| 8 | Code Forge (Woodpecker) | omni-woodpecker | 8000 | CI/CD |
| 9 | Code Fortress (SonarQube) | omni-sonarqube | 9000 | Quality |
| 10 | Security Shield | omni-security-shield | 8300 | Security |
| 11 | Container Manager (Portainer) | omni-portainer | 9443 | Infrastructure |
| 12 | Workflow Engine (n8n) | omni-n8n | 5678 | Orchestration |
| 13 | Observatory (Grafana) | omni-grafana | 3000 | Observability |
| 14 | Gateway Sentinel (Traefik) | omni-traefik | 80/443 | Infrastructure |
| 15 | Vector Memory (Qdrant) | omni-qdrant | 6333 | Knowledge |
| 16 | Semantic Cache | omni-semantic-cache | 6380 | Knowledge |
| 17 | AI Observability (Langfuse) | omni-langfuse | 3000 | Observability |
| 18 | Knowledge Ingestor | omni-knowledge-ingestor | 8400 | Knowledge |
| 19 | Freshness Monitor | omni-freshness-monitor | 8401 | Knowledge |
| 20 | Knowledge Base (Wiki.js) | omni-wikijs | 3000 | Knowledge |
| 21 | Object Store (MinIO) | omni-minio | 9000/9001 | Foundation |
| 22 | Source Control (Gitea) | omni-gitea | 3000 | Foundation |
| 23 | Authentication (Authentik) | omni-authentik | 9000 | Security |
| 24 | Cryptographic Fortress | omni-crypto | 8500 | Security |
| 25 | OMI Bridge | omni-omi-bridge | 8600 | Integration |
| 26 | Financial — Accounts | omni-accounts | 8701 | Business |
| 27 | Financial — Invoicing | omni-invoicing | 8702 | Business |
| 28 | Financial — Analytics | omni-analytics | 8703 | Business |
| 29 | Financial — CRM | omni-crm | 8704 | Business |
| 30 | AI Gateway | omni-ai-gateway | 8800 | AI |
| 31–34 | Database backends | omni-postgres, omni-redis, omni-neo4j, omni-elasticsearch | various | Data |
| 35 | Log Nexus (Loki) | omni-loki | 3100 | Observability |
| 36 | Neural Network (Rocket.Chat) | omni-rocketchat | 3000 | Communication |
| 37 | Integration Hub | omni-integration-hub | 8900 | Integration |
| 66 | Token Infinity | omni-token-infinity | 7600 | AI |
| 67 | Neo4j GraphRAG | omni-neo4j-graphrag-api | 7475 | Knowledge |

---

## Network Architecture

All services connect to the `omni-quantum-network` Docker bridge network. Inter-service communication uses container hostnames (e.g., `omni-litellm:4000`).

### External Access Flow
```
Client → Traefik (443) → Service (internal port)
                       → Authentik (OIDC) for protected routes
```

### Internal Communication Patterns
- **Synchronous**: REST/gRPC between services (e.g., Token Infinity → LiteLLM, Knowledge Ingestor → Qdrant)
- **Asynchronous**: n8n workflows, webhook-based event routing via Integration Hub
- **Streaming**: SSE/WebSocket for real-time updates (AI agents, chat)

---

## Data Flow — Knowledge Layer

```
┌────────────────┐     ┌─────────────────┐     ┌────────────────┐
│  Knowledge     │────▶│  Qdrant         │────▶│  Semantic      │
│  Ingestor      │     │  (embeddings)   │     │  Cache         │
└────────────────┘     └─────────────────┘     └────────────────┘
        │                      │                       │
        ▼                      ▼                       ▼
┌────────────────┐     ┌─────────────────┐     ┌────────────────┐
│  Freshness     │     │  Neo4j GraphRAG │     │  Token         │
│  Monitor       │     │  (patterns)     │     │  Infinity      │
└────────────────┘     └─────────────────┘     └────────────────┘
                               │                       │
                               ▼                       ▼
                       ┌─────────────────┐     ┌────────────────┐
                       │  Wiki.js        │     │  LiteLLM       │
                       │  (docs/runbooks)│     │  (completions) │
                       └─────────────────┘     └────────────────┘
```

---

## Security Architecture

- **Vault** (System 2): Centralized secrets management. All services retrieve credentials via Vault agent or API.
- **Authentik** (System 23): SSO/OIDC provider. Protects Wiki.js, Grafana, Portainer, n8n.
- **Security Shield** (System 10): Continuous vulnerability scanning of containers and dependencies.
- **Traefik** (System 14): TLS termination, IP allowlisting, rate limiting on all external endpoints.
- **Cryptographic Fortress** (System 24): Key management, encryption-at-rest, certificate lifecycle.

---

## Backup and Recovery

- **Duplicati** (System 1): Scheduled backups of all persistent volumes to MinIO object storage.
- **RPO**: 1 hour (hourly incremental backups)
- **RTO**: 30 minutes (automated restore scripts)
- **Backup targets**: PostgreSQL dumps, Redis RDB, Neo4j dumps, MinIO buckets, Gitea repos, Wiki.js data

---

## Resource Requirements

| Tier | CPU | Memory | GPU | Storage |
|------|-----|--------|-----|---------|
| Foundation | 4 cores | 8 GB | — | 100 GB |
| AI/ML | 8 cores | 32 GB | 1x NVIDIA (24GB+) | 200 GB |
| Knowledge | 4 cores | 16 GB | — | 100 GB |
| Observability | 2 cores | 8 GB | — | 50 GB |
| Business | 2 cores | 4 GB | — | 20 GB |
| **Total** | **20 cores** | **68 GB** | **1 GPU** | **470 GB** |

---

## Quick Start

```bash
# Clone the repository
git clone http://omni-gitea:3000/omni-admin/omni-quantum-elite.git
cd omni-quantum-elite

# Start all services
docker compose up -d

# Verify health
curl http://localhost:7475/health    # Neo4j GraphRAG API
curl http://localhost:4000/health    # LiteLLM
curl http://localhost:6333/health    # Qdrant
curl http://localhost:8401/health    # Freshness Monitor
```

---

*Last updated: 2025-01-01 | Maintained by the Omni Quantum Elite platform team*
