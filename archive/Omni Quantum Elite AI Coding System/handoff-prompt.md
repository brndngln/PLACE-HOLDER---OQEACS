# CONTINUATION PROMPT — Omni Quantum Elite AI Coding System
## PICK UP: Build Final 9 Systems (STANDARD PRIORITY 29-37)

---

## WHAT I'M BUILDING

The **Omni Quantum Elite AI Coding System** — a fully autonomous, enterprise-grade software development platform that transforms plain English descriptions into production-ready applications.

### Core Principles (NON-NEGOTIABLE)
- **100% Open Source** — Every component is auditable
- **100% Free** — Zero licensing costs ever
- **100% Self-Hostable** — Complete data ownership on MY servers
- **ZERO External Dependencies** — No vendor lock-in
- **ZERO Token/Rate Limits** — Unlimited capacity via Token Infinity System
- **Mattermost** for all communication (NOT Slack — fully open source, self-hosted)

---

## ARCHITECTURE OVERVIEW

### 26-Service Docker Infrastructure

| Category | Services |
|----------|----------|
| **AI Services** | Ollama, LiteLLM, OpenHands, SWE-Agent |
| **Orchestration** | n8n, n8n-worker |
| **External APIs** | Nango, Nango-worker (250+ integrations via OAuth) |
| **RAG/Memory** | Qdrant (vector database) |
| **Observability** | Langfuse, Promptfoo, Prometheus, Grafana |
| **Infrastructure** | PostgreSQL 16, Redis 7, MinIO (S3-compatible storage) |
| **Git/Deploy** | Gitea, Coolify, Caddy, Private Registry |
| **Project Mgmt** | Plane (web, api, worker, beat-worker) |
| **Communication** | Mattermost (with bots: alertbot, aibot, cicdbot) |
| **Wearable** | Omi Command Center |
| **AI Workflows** | Flowise (visual LLM workflow builder) |
| **Knowledge** | Wiki.js |
| **Analytics** | Apache Superset |
| **Scheduling** | Cal.com |
| **CRM** | Twenty CRM |
| **Invoicing** | Crater |
| **Financial** | Financial Fortress (tax, expense, subscription tracking) |

### Docker Network
- Network name: `omni-quantum-network`
- All services use labels: `omni.quantum.component=<name>`, `omni.quantum.tier=<tier>`, `omni.quantum.critical=<bool>`
- Prometheus scrape labels: `prometheus.scrape=true`, `prometheus.port=<port>`
- All services use `restart: unless-stopped`
- Logging uses shared YAML anchor `*default-logging`
- Health checks on every service with `interval`, `timeout`, `retries`, `start_period`

### 8-Stage Quality Pipeline

| Stage | Name | Purpose | Agents |
|-------|------|---------|--------|
| 0 | Spec Lock | Kill ambiguity before code | Product Spec, API Contract, Data Model, Threat Model |
| 1 | MVP Generation | Produce working vertical slice | Planner, Implementer, Test Writer |
| 2 | Backend Correctness | Eliminate AI backend failures | API Correctness, DB Integrity, Auth/Permissions, Error Handling, Migration |
| 3 | Architecture Refactor | Production-grade structure | Architecture, Boundary, Type Safety, Observability, Performance, I18n |
| 4 | Adversarial Review | Multi-model attack on mistakes | Bug Hunter, Security Auditor, Performance Auditor, UX/DX Auditor, Accessibility |
| 5 | Security Hardening | Zero-tolerance security | Tools only (Semgrep, Bandit, Trivy, etc.) |
| 6 | Release Engineering | Deployable & rollbackable | CI Pipeline, Dockerization, Deployment, Rollback, Documentation |
| 7 | Regression Lock | Never get worse | Eval gates (Promptfoo, Langfuse) |

### Token Infinity System (♾️ Unlimited AI)

| Tier | Providers | Daily Capacity |
|------|-----------|----------------|
| Local (Tier 1) | Ollama, vLLM | UNLIMITED |
| High-Speed (Tier 2) | Groq, Gemini, Mistral | ~5M tokens |
| Aggregators (Tier 3) | OpenRouter, Together | ~1.5M tokens |
| Community (Tier 4) | ApiFreeLLM, etc. | UNLIMITED |
| **TOTAL** | **50+ providers** | **EFFECTIVELY UNLIMITED** |

Features: Automatic failover (<100ms), intelligent load balancing, real-time health monitoring, automatic key rotation, circuit breakers.

---

## ALL 28 COMPLETED SYSTEMS ✅

### CRITICAL PRIORITY (Systems 1-7) — DONE ✅

| # | System | Codename | What It Does |
|---|--------|----------|--------------|
| 1 | Backup & Disaster Recovery | Backup Fortress / Data Fortress | Military-grade Restic backups — PostgreSQL/Redis/Qdrant backup managers, hourly/daily/weekly/monthly schedules, AES-256 encryption, point-in-time recovery, verified restores, off-site replication, <5 min RTO |
| 2 | Secrets Vault | Cryptographic Fortress | HashiCorp Vault — KV v2, database, transit, PKI engines, AppRole auth, fine-grained policies, automatic rotation, audit logging, Docker integration |
| 3 | Identity & Auth | Identity Fortress | Authentik — SSO, MFA, OAuth2/OIDC provider for all services |
| 4 | Database Management | Data Nucleus | PostgreSQL 16 + PgBouncer — auto-provisioning per project, connection pooling, schema migration management |
| 5 | Email Infrastructure | Message Forge | Postal + Listmonk — transactional email, newsletters, DKIM/SPF/DMARC |
| 6 | Centralized Logging | Log Nexus | Loki + Promtail — LogQL alerting, structured logging, retention policies |
| 7 | Security / IDS | Cyber Fortress | CrowdSec IPS + ModSecurity WAF + Fail2ban + custom IDS — 6-layer defense, threat intelligence feeds, automated blocking, honeypots |

### HIGH PRIORITY (Systems 8-17) — DONE ✅

| # | System | Codename | What It Does |
|---|--------|----------|--------------|
| 8 | Monitoring Stack | Pulse Command | Prometheus + Grafana + Thanos + Alertmanager — metrics collection, dashboards, multi-service alerting, exporters for every service |
| 9 | Reverse Proxy | Gateway Sentinel | Caddy — auto-SSL, rate limiting, auth forwarding, middleware chains |
| 10 | Container Management | Fleet Commander | Portainer + Watchtower + Autoheal + Dozzle + Docker-GC — container orchestration, auto-updates, self-healing, log viewing, cleanup |
| 11 | AI Gateway | Token Infinity | LiteLLM + Ollama — multi-tier model routing, 50+ free providers, failover chains, circuit breakers, load balancing |
| 12 | Workflow Automation | Flow Architect | n8n — queue mode, workers, webhook processing, 400+ integrations |
| 13 | Git Hosting | Code Citadel | Gitea — CI/CD runners, OAuth, LFS, repo mirroring |
| 14 | Project Management | Mission Control | Plane — boards, sprints, issues, workers, beat scheduler, OAuth |
| 15 | Team Communication | Comm Nexus | Mattermost — team chat, bots (alertbot, aibot, cicdbot), webhooks, metrics |
| 16 | AI Observability | AI Insights | Langfuse — LLM tracing, prompt versioning, evaluation, cost tracking |
| 17 | Vector Database | Memory Vault | Qdrant — embeddings storage, similarity search, collections, snapshots |

### MEDIUM PRIORITY (Systems 18-28) — DONE ✅

| # | System | Codename | What It Does |
|---|--------|----------|--------------|
| 18 | AI Coding Agent | OpenHands | Autonomous code generation/modification agent |
| 19 | AI Software Engineer | SWE-Agent | Autonomous GitHub issue resolution agent |
| 20 | API Integration Platform | Nango | Unified OAuth + 250+ API integrations (GitHub, Jira, Stripe, etc.) |
| 21 | Object Storage | MinIO | S3-compatible self-hosted storage — artifacts, assets, backups |
| 22 | Wearable Integration | Omi Command Center | Omi device connectivity — voice commands ("Hey Omi, build me a..."), build notifications, status checks, deploy commands |
| 23 | Knowledge Base | Wiki.js | Internal documentation, wikis, Markdown/WYSIWYG, Git-backed |
| 24 | Analytics Engine | Apache Superset | Business intelligence, data visualization, SQL Lab, dashboards |
| 25 | Scheduling System | Cal.com | Calendar/booking — appointments, resource scheduling, webhooks |
| 26 | CRM System | Twenty CRM | Customer relations — contacts, deals, pipeline, companies |
| 27 | Invoice System | Crater | Billing — invoice generation, payment tracking, estimates, expenses |
| 28 | AI Visual Workflows | Flowise | Visual LLM chain/agent builder — drag-and-drop AI workflow creation, chatflows, agentflows, tools, assistants |

---

## WHAT TO BUILD NOW — STANDARD PRIORITY (Systems 29-37) 🚧

These are the **infrastructure, ops, and developer experience** layer — the systems that make everything production-hardened, observable, recoverable, and easy to manage.

### System 29: Enhanced Monitoring Stack
- **Purpose**: Production-grade observability across ALL 28 existing services
- **Core**: Prometheus + Grafana (already exist as System 8 "Pulse Command" — this ENHANCES them)
- **Enhancements needed**: Custom dashboards per service, SLA tracking, capacity planning, anomaly detection, business metrics (not just infra), unified alerting rules across all 28 services
- **Integrations**: Alert to Mattermost #alerts channel, Omi wearable notifications, n8n webhook triggers

### System 30: Log Aggregation (Enhanced)
- **Purpose**: Production-grade centralized logging with search & retention
- **Core**: Loki + Promtail (already exist as System 6 "Log Nexus" — this ENHANCES them)
- **Enhancements needed**: Structured logging standards for all 28 services, log correlation across services (trace IDs), retention policies (hot/warm/cold), log-based alerting, error pattern detection, Grafana log dashboards
- **Integrations**: Link to Langfuse traces, security event correlation with Cyber Fortress

### System 31: Uptime Monitor
- **Purpose**: Health checks, public status page, incident management
- **Tool**: Uptime Kuma (100% open source, self-hosted)
- **Features**: HTTP/TCP/DNS/Docker health checks for all 28 services, public status page, incident notifications → Mattermost + Omi, maintenance windows, response time tracking, certificate expiry monitoring
- **Docker**: New service on `omni-quantum-network`

### System 32: Backup System (Enhanced)
- **Purpose**: Production-grade automated backup schedules for everything
- **Core**: Restic (already exists as System 1 "Backup Fortress" — this ENHANCES)
- **Enhancements needed**: Automated schedules for ALL 28 services' data (not just core DBs), MinIO bucket snapshots, Gitea repo backups, Mattermost data export, n8n workflow backups, Vault seal key backups, retention lifecycle management, backup testing/verification automation, cross-region replication setup

### System 33: Secret Management (Enhanced)
- **Purpose**: Centralized secrets for all 28 services
- **Core**: HashiCorp Vault (already exists as System 2 "Cryptographic Fortress" — this ENHANCES)
- **Enhancements needed**: SOPS integration for git-encrypted secrets, dynamic secrets for all database connections, PKI certificate auto-issuance for service-to-service TLS, automatic rotation schedules for all API keys, audit trail dashboards, emergency break-glass procedures

### System 34: Reverse Proxy / SSL (Enhanced)
- **Purpose**: Production-grade edge routing for all services
- **Core**: Caddy (already exists as System 9 "Gateway Sentinel" — ENHANCE or MIGRATE to Traefik)
- **Enhancements needed**: Auto-SSL via Let's Encrypt for all services, rate limiting per endpoint, IP whitelisting, geo-blocking, middleware chains (auth → rate-limit → compress → route), dashboard for route management, mTLS for internal service communication
- **Consideration**: Evaluate Traefik vs. keeping Caddy (both are open source, self-hosted)

### System 35: CI/CD Pipelines
- **Purpose**: Build, test, deploy automation for all generated applications
- **Tool**: Gitea Actions (built into existing Gitea) and/or Woodpecker CI (100% open source)
- **Features**: Auto-triggered on push/PR, run full 8-stage quality pipeline, Docker image builds → Private Registry, deploy to Coolify, rollback capability, build status → Mattermost + Omi, artifact storage in MinIO
- **Integration with pipeline**: This IS the automation of the 8-stage pipeline (Stage 6: Release Engineering)

### System 36: Dev Environments
- **Purpose**: Browser-based standardized development workspaces
- **Tool**: Coder (open source) and/or Devcontainers
- **Features**: One-click dev environments per project, pre-configured with all tools (linters, formatters, LSPs), access via browser (VS Code Server), GPU passthrough for AI model testing, persistent workspaces, template library for common stacks
- **Docker**: New service(s) on `omni-quantum-network`

### System 37: Master Orchestrator (THE CAPSTONE)
- **Purpose**: Unified single-pane control over ALL 36 systems
- **Components**:
  - **CLI Tool**: `omni` command — `omni status`, `omni deploy`, `omni backup`, `omni build "make me a todo app"`, `omni health`, `omni logs`, `omni secrets rotate`
  - **Web Dashboard**: Single page showing status of all 36 systems, health, metrics, recent builds, active deployments
  - **API Layer**: REST + WebSocket API that other systems can call
  - **Omi Integration**: Voice-first control interface wrapping the CLI
  - **Mattermost Bot**: Chat-based control (`@omni deploy staging`, `@omni status all`)
- **This ties EVERYTHING together into one control plane**

---

## IMPLEMENTATION STANDARDS

### Docker Compose Conventions
```yaml
services:
  service-name:
    image: <image>:<version>  # Always pin versions
    container_name: omni-<service-name>
    environment:
      - KEY=value
    volumes:
      - ./data/<service>:/data
    ports:
      - "HOST:CONTAINER"
    healthcheck:
      test: ["CMD", "..."]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    logging: *default-logging
    networks:
      - omni-quantum-network
    labels:
      - "omni.quantum.component=<name>"
      - "omni.quantum.tier=<tier>"
      - "omni.quantum.critical=<true|false>"
      - "prometheus.scrape=true"
      - "prometheus.port=<port>"

networks:
  omni-quantum-network:
    external: true
```

### Quality Standards for Each System
1. **Complete Docker Compose** with health checks, labels, logging
2. **Python SDK/Client** for programmatic access from other systems
3. **Init/Setup Script** — automated first-run configuration
4. **Mattermost Integration** — notifications to appropriate channels
5. **Prometheus Metrics** — exposed and scraped
6. **Grafana Dashboard** — pre-built JSON dashboard
7. **Backup Integration** — data included in Backup Fortress schedules
8. **Vault Integration** — secrets stored in/pulled from Vault
9. **Omi Webhooks** — critical events sent to wearable

### File Structure Pattern
```
system-name/
├── docker-compose.yml
├── config/
│   ├── <service>.conf
│   └── ...
├── scripts/
│   ├── init.sh
│   ├── setup.py
│   └── ...
├── sdk/
│   └── client.py
├── dashboards/
│   └── grafana-<service>.json
├── alerts/
│   └── rules.yml
└── README.md
```

---

## INSTRUCTIONS

Build ALL 9 systems (29-37) with the same level of extreme, production-grade detail as the previous 28 systems. Each system needs:

1. Full Docker Compose configuration
2. All config files
3. Python SDK/client class
4. Init/setup scripts
5. Grafana dashboard JSON
6. Prometheus alert rules
7. Mattermost webhook integration
8. Integration points with existing systems
9. Master setup script that deploys everything

For systems that ENHANCE existing ones (29, 30, 32, 33, 34), build the enhancements as additions — don't rebuild what's already there.

System 37 (Master Orchestrator) is the CAPSTONE — it should provide a unified CLI + web dashboard + API that controls all 36 other systems as one cohesive platform.

**GO. Build all 9 systems. Make them INSANELY comprehensive.**
