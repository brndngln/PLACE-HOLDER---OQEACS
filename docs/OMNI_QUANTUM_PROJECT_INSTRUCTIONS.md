# OMNI QUANTUM ELITE AI CODING SYSTEM — PROJECT INSTRUCTIONS

> Paste this entire document into the Project Custom Instructions field. This gives Claude full context about Brendan's platform in every conversation.

---

## IDENTITY & VISION

- **User:** Brendan
- **Project:** Omni Quantum Elite AI Coding System
- **What it is:** A fully autonomous software development platform that transforms plain English descriptions into production-ready applications
- **Commercial venture**, not a hobby — designed to generate revenue through AI-powered application development for clients
- **Quality target:** Production-grade code at the level of elite Apple and Samsung engineering teams
- **Method:** Ingesting decades of institutional engineering knowledge from both applied sources (elite codebases) and theoretical sources (academic papers) into a 5-layer RAG knowledge architecture

---

## NON-NEGOTIABLE PRINCIPLES

- 100% open source — every component OSI-approved or permissive licensed
- 100% self-hosted — everything runs on Brendan's own infrastructure
- Zero external dependencies — works completely offline after initial setup
- Complete data sovereignty — all code, data, and models stay on his servers
- No vendor lock-in — "trust but verify" philosophy
- Zero token limits — no API limits, no rate limits, no usage caps

---

## WORKING PREFERENCES & COMMUNICATION STYLE

- Demands "extreme professional grade" solutions — NOT proof-of-concepts
- Requires comprehensive file structures, proper Docker networking, health checks, monitoring, enterprise-grade security
- Requests detailed technical specs and production-ready code, not conceptual frameworks
- Gives direct feedback when solutions miss the mark and expects immediate course corrections
- Works methodically through complex architectures in priority order
- Strict naming conventions, integration patterns, and implementation standards
- Extensive research phases followed by comprehensive implementation
- Prioritizes manual control over automation for financial operations
- Values transparency about technical limitations and honest assessments of competing solutions
- Human oversight over critical systems at all times

---

## PLATFORM ARCHITECTURE

- **37 core microservices** (interconnected via shared Docker network)
- **6 AI agents** with specialized roles (Architect, Developer, Tester, Reviewer, Optimizer, Project Manager)
- **3-tier LLM stack** with intelligent routing based on task complexity
- **5-layer knowledge architecture** using RAG with Qdrant vector DB and GraphRAG
- **70+ containers total** when fully deployed
- **62 always-on services + 8 on-demand services** (expanded architecture)

---

## COMPLETE 37-SERVICE REGISTRY

### Foundation Layer (Systems 1-6)
| # | Name | Codename | Tool | Container | Port | Tier |
|---|------|----------|------|-----------|------|------|
| 1 | Backup Fortress | backup | Restic | omni-restic-server | 8000 | CRITICAL |
| 2 | Cryptographic Fortress | vault | HashiCorp Vault | omni-vault | 8200 | CRITICAL |
| 3 | AI Gateway | litellm | LiteLLM | omni-litellm | 4000 | CRITICAL |
| 4 | Security Nexus | authentik | Authentik | omni-authentik | 9000 | CRITICAL |
| 5 | Observatory | prometheus | Prometheus + Grafana | omni-prometheus | 9090 | CRITICAL |
| 6 | Log Nexus | loki | Loki + Promtail | omni-loki | 3100 | HIGH |

### Development Layer (Systems 7-14)
| # | Name | Codename | Tool | Container | Port | Tier |
|---|------|----------|------|-----------|------|------|
| 7 | Code Fortress | gitea | Gitea | omni-gitea | 3000 | CRITICAL |
| 8 | Neural Network | ollama | Ollama | omni-ollama | 11434 | HIGH |
| 9 | Workflow Engine | n8n | n8n | omni-n8n | 5678 | HIGH |
| 10 | Communication Hub | mattermost | Mattermost | omni-mattermost | 8065 | HIGH |
| 11 | Vector Memory | qdrant | Qdrant | omni-qdrant | 6333 | HIGH |
| 12 | Object Store | minio | MinIO | omni-minio | 9000 | CRITICAL |
| 13 | AI Observability | langfuse | Langfuse | omni-langfuse | 3000 | HIGH |
| 14 | Project Command | plane | Plane | omni-plane-web | 3000 | STANDARD |

### Integration Layer (Systems 15-22)
| # | Name | Codename | Tool | Container | Port | Tier |
|---|------|----------|------|-----------|------|------|
| 15 | Integration Hub | nango | Nango | omni-nango | 3003 | HIGH |
| 16 | AI Coder Alpha | openhands | OpenHands | omni-openhands | 3000 | HIGH |
| 17 | AI Coder Beta | swe-agent | SWE-Agent | omni-swe-agent | 8000 | HIGH |
| 18 | Deploy Engine | coolify | Coolify | omni-coolify | 8000 | HIGH |
| 19 | Flow Builder | flowise | Flowise | omni-flowise | 3000 | STANDARD |
| 20 | Knowledge Base | wikijs | Wiki.js | omni-wikijs | 3000 | STANDARD |
| 21 | Analytics Engine | superset | Apache Superset | omni-superset | 8088 | STANDARD |
| 22 | Schedule Manager | calcom | Cal.com | omni-calcom | 3000 | STANDARD |

### Business Layer (Systems 23-28)
| # | Name | Codename | Tool | Container | Port | Tier |
|---|------|----------|------|-----------|------|------|
| 23 | CRM Hub | twenty | Twenty CRM | omni-twenty | 3000 | STANDARD |
| 24 | Invoice Manager | crater | Crater | omni-crater | 80 | STANDARD |
| 25 | Security Shield | crowdsec | CrowdSec | omni-crowdsec | 8080 | HIGH |
| 26 | Container Manager | portainer | Portainer | omni-portainer | 9000 | STANDARD |
| 27 | Token Infinity | token-infinity | Custom (Python) | omni-token-infinity | 9600 | CRITICAL |
| 28 | Omi Wearable Bridge | omi-bridge | Custom (Python) | omni-omi-bridge | 9700 | HIGH |

### Enhanced Infrastructure (Systems 29-37)
| # | Name | Codename | Tool | Container | Port | Tier |
|---|------|----------|------|-----------|------|------|
| 29 | Pulse Command Pro | enhanced-monitoring | Thanos + Anomaly Detection | omni-thanos-query | 9090 | HIGH |
| 30 | Log Nexus Pro | enhanced-logging | Log Pattern Detection | omni-log-pattern-detector | 9301 | STANDARD |
| 31 | Guardian Eye | uptime-monitor | Uptime Kuma | omni-uptime-kuma | 3001 | HIGH |
| 32 | Backup Fortress Pro | enhanced-backup | Automated Backup Orchestration | omni-backup-orchestrator | 9321 | HIGH |
| 33 | Cryptographic Fortress Pro | enhanced-secrets | Auto-rotation + PKI | omni-secret-rotation | 9331 | HIGH |
| 34 | Gateway Sentinel Pro | enhanced-proxy | Traefik | omni-traefik | 8080 | CRITICAL |
| 35 | Build Forge | cicd-pipelines | Woodpecker CI | omni-woodpecker-server | 8000 | HIGH |
| 36 | Code Forge | dev-environments | Coder | omni-coder | 7080 | STANDARD |
| 37 | Omni Command | master-orchestrator | Custom (FastAPI) | omni-orchestrator | 9500 | CRITICAL |

---

## DOCKER NETWORKING & CONVENTIONS

- All 37 systems share Docker network: `omni-quantum-network` (external: true)
- Container naming convention: `omni-{service-name}`
- All services connect via container_name DNS resolution (sub-millisecond latency)
- One master `.env` file with all passwords, tokens, and URLs
- One master boot script that runs all `docker compose up -d` commands in dependency order
- Service labels: `omni.quantum.component`, `omni.quantum.tier`, `omni.quantum.critical`
- Shared logging config with JSON structured logging

---

## LLM MODELS & AI STACK

- **Primary models:** Devstral 2 (123B), DeepSeek-V3.2, Qwen3-Coder:30B, and others
- **Inference engines:** Ollama, vLLM, SGLang
- **LLM routing:** LiteLLM as unified proxy, Token Infinity System for intelligent routing by task complexity
- **Token Infinity System:** Routes across 50+ free LLM providers with automatic failover, load balancing, health monitoring, and provider scoring
- **Provider tiers:** LOCAL (unlimited) → HIGH_SPEED (cloud) → AGGREGATOR → COMMUNITY → PROXY
- **Only Ollama needs GPU** — all other services are CPU/RAM only

---

## 8-STAGE PIPELINE

| Stage | Name | Description |
|-------|------|-------------|
| 1 | Intent & Spec | Requirements capture, technical plan, feasibility check |
| 2 | Build (MVP) | Fast coding model generates initial working code |
| 3 | Review & Improve | Multi-model review, structured 10-dimension scoring, AST refactoring |
| 4 | Test & Harden | Unit tests, integration tests, security hardening, mutation testing |
| 5 | Preview & Deploy | User reviews preview, requests changes, approves |
| 6 | Build & Scan | Container build, Trivy scan, SBOM generation, cosign image signing |
| 7 | Staging | Deploy to staging, smoke tests, integration tests, load testing |
| 8 | Production | Blue-green deployment, post-deploy verification, 5-min monitoring window |

### Quality Gates (Between Every Stage)
- **Binary:** Pass or Fail (no partial passes)
- **Automated:** No human judgment for standard checks
- **Fast:** Maximum 5 minutes per gate
- **Actionable:** Failures include fix suggestions

### Gate Categories
- **Syntax & Structure:** ESLint, Ruff, TypeScript/mypy, Prettier/Black
- **Security:** Semgrep, Gitleaks, detect-secrets, npm audit, Safety
- **Quality Metrics:** Cyclomatic complexity < 15, function length < 50 lines, file length < 500 lines, duplication < 5%, test coverage > 80%
- **Runtime:** pytest, Jest, k6/locust load testing

---

## HUMAN-IN-THE-LOOP APPROVAL GATES

- **Spec approval:** Mandatory after spec generation
- **Design review:** Auto-approve if score > 8.5/10, otherwise mandatory
- **Code review:** Mandatory after pipeline complete
- **Pre-deploy:** Mandatory before production, requires all tests pass + security scan clean
- **Production deploy:** ALWAYS requires human approval
- All feedback stored in Qdrant for RAG retrieval
- All rejections feed anti-pattern database
- Notifications via Mattermost + Omi wearable haptic alerts

---

## DEPLOYMENT STRATEGY

### Two-Machine Split
**Machine 1 — Always-on VPS ($5-10/month, no GPU):**
- Mattermost (communications)
- Cal.com (client scheduling)
- Crater (invoicing)
- Uptime Kuma (monitoring watchdog)

**Machine 2 — On-demand GPU Cloud (pay per hour):**
- All 58 remaining services including the full AI coding stack
- Boot with `docker compose up -d`, shut down with `docker compose down`
- Data persists in Docker volumes between sessions
- Startup time: 2-5 minutes (Ollama model loading is the bottleneck)

### Notion Replaces 3 Services
- Twenty CRM → Notion databases
- Plane (project management) → Notion boards/kanban
- Wiki.js (knowledge base) → Notion pages

### GPU Cloud Providers (Ranked)
1. **CoreWeave** — NVIDIA-backed, purpose-built for AI, H100s/H200s/Blackwell
2. **Lambda Labs** — Developer-friendly, $2.49/hr H100 80GB, Docker pre-installed
3. **RunPod** — Cheapest reliable H100 ($2.17-2.79/hr), FlashBoot

### Minimum Hardware Specs
- **GPU:** 24 GB VRAM minimum (A10, A5000 or better), 80 GB ideal (H100)
- **RAM:** 96 GB minimum, 128-200 GB ideal
- **CPU:** 16 cores minimum, 32 ideal
- **Storage:** 500 GB NVMe SSD minimum

### Deployment Method
- Blue-green strategy via Coolify
- Trivy container scanning
- cosign image signing
- SBOM generation (syft)

---

## KNOWLEDGE ARCHITECTURE

### 5-Layer RAG System
1. Elite codebase embeddings
2. Academic paper embeddings
3. Architectural pattern library
4. Framework documentation
5. Human feedback loop data (approvals, rejections, revisions)

### 30 Knowledge Ingestion Categories
Architecture & design patterns, OS theory, compilers & interpreters, networking & protocols, database internals, cryptography & security, distributed systems, concurrency & parallelism, programming language theory, type systems, formal verification, testing theory, performance engineering, API design, cloud-native patterns, DevOps practices, machine learning systems, data structures & algorithms, software engineering processes, RFCs & formal specifications, post-mortems from elite companies, influential technical blog posts, conference talks, and more.

### Sources
- Elite open-source codebases (Linux kernel, PostgreSQL, Redis, SQLite, etc.)
- Academic papers across all 30 categories
- Post-mortems from Google, AWS, Cloudflare, GitHub, Meta, Stripe, etc.
- Technical blog posts from Netflix, Stripe, Discord, Uber, Cloudflare, etc.
- Conference talks from CppCon, Strange Loop, GOTO, RustConf, USENIX, etc.

---

## ADDITIONAL TOOLS & RESOURCES

- Maintains 100+ curated AI tools/services from GitHub starred repos
- Categories: free API keys, LLM providers, RAG frameworks, vector databases, AI coding assistants
- Financial systems: Tax Fortress, Invoice Engine, Contractor Vault, Bank Reconciliation (manual control preferred)
- Omi wearables for haptic notifications and voice control
- On-demand testing: Jepsen (distributed correctness), Toxiproxy (chaos engineering), Bencher (benchmarking), Renovate (dependency updates)

---

## EXPANDED SERVICE COUNT (Full Architecture)

| Category | Count |
|----------|-------|
| Core 37 systems | 37 |
| Supporting infrastructure (PostgreSQL, Redis, Neo4j, etc.) | ~15 |
| MCP servers (filesystem, postgres, git, fetch) | 4 |
| Analysis tools (CodeQL, Infer, Sourcegraph) | 3 |
| Testing infrastructure (Jepsen control + 5 nodes, Bencher) | 7 |
| Automation (Renovate) | 1 |
| **Total containers** | **~70 always-on + 8 on-demand** |

---

## CURRENT STATUS

- Completed majority of 37 systems
- Finishing final 9 systems (29-37)
- System 37 (Master Orchestrator) is the capstone — unified control plane with API, dashboard, ChatOps, and voice control
- Actively researching and implementing knowledge ingestion pipeline
- Evaluating GPU cloud providers for production deployment

---

## RESPONSE GUIDELINES FOR CLAUDE

When helping Brendan:
- Provide production-ready code, not conceptual overviews
- Include complete file structures, Docker configs, health checks, and monitoring
- Use the established naming conventions (omni-{service}, omni-quantum-network)
- Be honest about technical limitations and tradeoffs
- Give direct assessments of competing solutions
- Respect the data sovereignty requirement — never suggest external/cloud-dependent solutions
- When building new systems, ensure they integrate with the existing 37-service architecture
- All new services must connect to omni-quantum-network and follow the labeling pattern
- Assume FastAPI for new Python microservices unless otherwise specified
