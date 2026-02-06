# ⚛ OMNI QUANTUM ELITE — MASTER BUILD PLAN
## The Definitive 843-Item Execution Blueprint

**Date:** February 4, 2026
**Author:** Claude (for Brendan)
**Scope:** Every distinct buildable component across all architecture documents
**Constraint Compliance:** 100% open-source · 100% self-hosted · Zero external dependencies

---

## EXECUTIVE SUMMARY

### What This Document Is

This is the complete, deduplicated, dependency-mapped, prioritized execution plan for building every remaining component of the Omni Quantum Elite AI Coding System. It takes the raw 843-item inventory, eliminates ~190 duplicates and overlaps, consolidates related items into 127 atomic "Build Units" (each representing a deployable, testable deliverable), and sequences them across 12 strategic Build Waves.

### Current State Assessment

| Layer | Status | Systems |
|-------|--------|---------|
| Foundation (1-7) | ✅ COMPLETE | Backup, Vault, LiteLLM, Authentik, Prometheus, Loki, Gitea |
| Development (8-17) | ✅ COMPLETE | Ollama, n8n, Mattermost, Qdrant, MinIO, Langfuse, Plane |
| Integration (18-28) | ✅ COMPLETE | OpenHands, SWE-Agent, Nango, Coolify, Flowise, Wiki.js, Superset, Cal.com, Twenty, Crater, CrowdSec, Portainer, Token Infinity, Omi Bridge |
| Enhanced Infra (29-37) | ✅ SPECIFIED | Thanos, Log Pro, Uptime Kuma, Backup Pro, Secrets Pro, Traefik, Woodpecker, Coder, Master Orchestrator |

**What remains:** The 843-item list represents everything BEYOND and AROUND the core 37 systems — the enhancement layers, tool integrations, verification pipelines, business workflows, knowledge ingestion, and operational capabilities that transform 37 services into an elite autonomous coding platform.

### The 12 Build Waves

| Wave | Name | Build Units | Est. Effort | Cumulative Value |
|------|------|-------------|-------------|------------------|
| 0 | **Foundation Lock** | 8 | 1 week | Systems 29-37 deployed, platform boots reliably |
| 1 | **Verification Core** | 12 | 2 weeks | Code quality gates operational, pipeline runs end-to-end |
| 2 | **Context Intelligence** | 10 | 2 weeks | Agents get smart context, not raw dumps |
| 3 | **Security Hardening** | 11 | 1.5 weeks | Supply chain, secrets, threat modeling locked down |
| 4 | **Knowledge Engine** | 14 | 2.5 weeks | RAG ingestion operational across all 30 categories |
| 5 | **Client Revenue Pipeline** | 12 | 2 weeks | Intake → build → deliver → invoice workflow live |
| 6 | **Agent Intelligence** | 11 | 2 weeks | Multi-agent collaboration, prompt optimization, SERA |
| 7 | **Advanced Testing** | 13 | 2 weeks | Mutation, fuzzing, chaos, formal verification |
| 8 | **Business Infrastructure** | 15 | 2.5 weeks | Email, CRM, support, analytics, notifications |
| 9 | **Performance & Scale** | 10 | 1.5 weeks | Semantic caching, pipeline parallelization, profiling |
| 10 | **Specialized Capabilities** | 8 | 2 weeks | Mobile, IaC, ML pipeline, media processing |
| 11 | **Polish & Governance** | 9 | 1.5 weeks | Compliance, i18n, green engineering, disaster recovery |

**Total estimated effort:** ~22 weeks of focused implementation (single-developer pace)

---

## DEDUPLICATION ANALYSIS

The raw 843 items contain significant overlap across the 6 source documents. Here is the deduplication summary:

| Category | Raw Items | Duplicates Removed | Consolidated Build Units |
|----------|-----------|-------------------|-------------------------|
| Tools/Libraries (individual) | 247 | 89 | Bundled into parent systems |
| Complete Systems | 68 | 12 | 56 unique systems |
| Sub-components | 198 | 34 | Bundled into parent systems |
| Configuration Elements | 112 | 18 | Bundled into deployment scripts |
| Pipeline Stages/Gates | 87 | 22 | Consolidated into unified pipeline |
| Knowledge Modules | 64 | 8 | 56 unique knowledge units |
| Business Processes | 67 | 7 | 60 unique workflows |
| **TOTAL** | **843** | **~190** | **~653 unique items → 127 Build Units** |

**Key duplicates eliminated:**
- Loki/Promtail mentioned 4x across different sections → single enhanced logging build
- Uptime Kuma mentioned 3x → single uptime monitor build
- Unleash/feature flags mentioned 3x → single feature flag build
- Cal.com mentioned 3x → already built (System 25)
- Twenty CRM mentioned 2x → already built (System 26), now replaced by Notion
- Hadolint/Checkov mentioned 3x → single IaC linting build
- mutmut/Stryker mentioned 3x → single mutation testing build
- GlitchTip mentioned 2x → single error tracking build
- MLflow mentioned 2x → single ML experiment tracking build
- Renovate mentioned 2x → single dependency update build
- PgBouncer mentioned 2x → single connection pooling build

---

## WAVE 0: FOUNDATION LOCK
### *"Nothing else works until the platform boots reliably"*

**Goal:** Deploy Systems 29-37, master .env, boot script, health check chain.
**Duration:** 1 week
**Prerequisite:** Systems 1-28 running

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 0.1 | **Master .env Generator** | .env file, 150+ variables, Vault integration, secrets generation | `scripts/generate-env.sh` — generates all DB passwords, API tokens, webhook URLs, OAuth credentials. Pulls existing secrets from Vault, generates missing ones. |
| 0.2 | **PostgreSQL Database Creator** | 15+ databases, users, grants | `scripts/init-databases.sh` — creates all required PostgreSQL databases (gitea, mattermost, n8n, langfuse, plane, authentik, wikijs, superset, calcom, woodpecker, coder, sla_tracker, backup_orchestrator, master_orchestrator) with proper users and grants. |
| 0.3 | **Tiered Boot Orchestrator** | Tier 0-6 startup, health check gates, dependency ordering | `scripts/boot-platform.sh` — starts all services in dependency order with health-check gates between tiers. Tier 0 (PostgreSQL, Redis, MinIO, network) → Tier 1 (Vault, Traefik, Authentik, Prometheus, Loki) → Tier 2 (Ollama, LiteLLM, Gitea, Mattermost, Qdrant, Langfuse) → Tier 3 (n8n, Plane, Nango, Flowise, etc.) → Tier 4 (OpenHands, SWE-Agent, Token Infinity, Omi Bridge) → Tier 5 (Systems 29-36) → Tier 6 (Master Orchestrator). |
| 0.4 | **Systems 29-34 Deployment** | Enhanced monitoring, logging, uptime, backup, secrets, proxy | 6 docker-compose files, all configs, init scripts. Each with health checks, labels, Prometheus metrics. |
| 0.5 | **System 35: Build Forge** | Woodpecker CI, 8-stage pipeline template, Gitea webhook | docker-compose + pipeline YAML template that implements the full 8-stage quality pipeline. |
| 0.6 | **System 36: Code Forge** | Coder, workspace templates, GPU passthrough | docker-compose + Terraform workspace template for standardized dev environments. |
| 0.7 | **System 37: Master Orchestrator** | REST API, Dashboard, ChatOps bot, Voice bridge, Event bus | The capstone. 5 services (API :9500, Dashboard :9501, Bot, Voice :9502, Events). Unified control plane for all 36 services. |
| 0.8 | **Init Scripts Bundle** | Vault policies, Authentik OAuth apps, Gitea admin tokens, Mattermost bots, MinIO buckets, Prometheus config, Uptime Kuma monitors, Grafana dashboards | `scripts/init-all.sh` — runs all post-boot initialization in correct order. |

**Exit Criteria:** `omni status` shows all 37 systems green. Full platform boot from cold in < 5 minutes (excluding model loading).

---

## WAVE 1: VERIFICATION CORE
### *"Trust nothing the AI generates until it proves itself"*

**Goal:** Implement the 4-tier verification pipeline, quality gates, and code review scoring.
**Duration:** 2 weeks
**Prerequisite:** Wave 0 complete (Build Forge running)

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 1.1 | **Tier 1 — Instant Verification (< 5s)** | Type checking (pyright, tsc --strict), linting (Ruff, ESLint/oxlint), formatting (Black/Prettier), import validation (deptry) | Woodpecker pipeline step: `instant-verify`. Runs on every commit. All tools installed in a single Docker image `omni-verify-instant`. |
| 1.2 | **Tier 2 — Fast Verification (< 60s)** | Unit tests (pytest, Jest/vitest), Semgrep security scan, API contract validation (Spectral), secret detection (gitleaks, detect-secrets) | Woodpecker pipeline step: `fast-verify`. Parallel execution of 4 sub-steps. |
| 1.3 | **Tier 3 — Deep Verification (< 10min)** | Integration tests (Testcontainers), CodeQL semantic analysis, Facebook Infer, performance benchmarks vs baseline | Woodpecker pipeline step: `deep-verify`. Docker image `omni-verify-deep` with CodeQL, Infer pre-installed. |
| 1.4 | **Tier 4 — Exhaustive (Nightly)** | Fuzz testing (AFL++, Atheris, cargo-fuzz), mutation testing (mutmut, Stryker, cargo-mutants), full dependency vuln scan (Trivy, Grype, OSV-Scanner), license compliance (ScanCode, licensee), technical debt quantification | Nightly Woodpecker pipeline. Results → Grafana dashboard + Mattermost #quality channel. |
| 1.5 | **10-Dimension Code Review Scoring** | Correctness, Security, Performance, Error handling, Readability, Testability, API design, Observability, Documentation, Standards compliance | FastAPI service `omni-code-scorer` (:8350). Takes code + spec → returns structured JSON score per dimension. Uses Qdrant to store all scores. |
| 1.6 | **Quality Gate Engine** | Binary pass/fail gates, max 5min, actionable failure messages, fix suggestions | FastAPI service `omni-gate-engine` (:8351). Evaluates all gate categories. Blocks pipeline progression on failure. Integrates with Build Forge webhook. |
| 1.7 | **Semantic Intent Verification** | Separate-model verification agent, spec-to-code behavior comparison | Agent that uses a DIFFERENT model from the generator to read the spec and verify the code matches intent. Catches correlated hallucination failures. |
| 1.8 | **Hallucinated Dependency Checker** | PyPI/npm registry API queries, package existence, typosquatting detection, minimum download threshold | Python script in pipeline: checks every import/require against real registries. Flags non-existent packages, suspicious names, low-download packages. |
| 1.9 | **Clean-Room Reproducibility** | Fresh container builds, no-cache, dependency completeness | Woodpecker step: builds project in a fresh container with `--no-cache`. If it fails → dependency spec is incomplete. |
| 1.10 | **Architecture Rule Enforcement** | 12-Factor App checklist, DDD layer rules, dependency-cruiser, ArchUnit patterns | Config-as-code rules checked in Tier 1. Violations block the pipeline. |
| 1.11 | **Sourcegraph Code Intelligence** | Code search, cross-reference, go-to-definition across all repos | Docker service `omni-sourcegraph` (:7080). Indexes all Gitea repos. Provides code context to agents. |
| 1.12 | **ADR (Architecture Decision Records)** | ADR templates, ADR search via Qdrant, mandatory ADR for significant changes | Template in project scaffolding. ADRs stored in repo + embedded in Qdrant for agent retrieval. |

**Exit Criteria:** A test commit flows through all 4 verification tiers. Intentionally bad code (SQL injection, missing tests, hallucinated imports) is caught and blocked.

---

## WAVE 2: CONTEXT INTELLIGENCE
### *"Context engineering is the new prompt engineering"*

**Goal:** Build the context compilation layer that feeds agents the right information at the right time.
**Duration:** 2 weeks
**Prerequisite:** Wave 1 complete (verification pipeline operational)

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 2.1 | **Context Compiler Service** | omni-context-compiler (:8325), 4 context assembly stages | FastAPI service. Takes task description → assembles optimal context window: relevant code (via Sourcegraph), patterns (via Qdrant), anti-patterns, tool descriptions, error history. |
| 2.2 | **Tool Selection Intelligence** | RAG over 125+ tool descriptions, top-k retrieval per step | Qdrant collection `tool_descriptions`. Each tool has vector embedding. Before each agent step, retrieve only 5-10 most relevant tools. |
| 2.3 | **MCP Server: Package Registry** | Package lookup, version resolution, compatibility check | MCP server (Streamable HTTP) that agents call to verify packages exist and check compatibility. |
| 2.4 | **MCP Server: Documentation** | Framework docs retrieval, API reference lookup | MCP server providing RAG-based documentation search across all indexed framework docs. |
| 2.5 | **MCP Server: Database Schema** | Schema introspection, migration validation | MCP server that reads live database schemas and provides them to agents for query generation. |
| 2.6 | **MCP Server: Pipeline Tools** | Lint/test/scan invocation from agent context | MCP server exposing analysis tools so agents can run verification during generation (not just after). |
| 2.7 | **Anti-Pattern Knowledge Base** | Initial 50+ entries, continuous growth from rejections, CWE mapping | Qdrant collection `anti_patterns`. Seeded with common AI-generated code mistakes. Every pipeline rejection adds a new entry. Agents receive relevant anti-patterns in context. |
| 2.8 | **Prompt Decay Detection** | Weekly golden test suite, quality score tracking, forced refresh triggers | Scheduler runs golden test suite weekly. If agent output quality drops below threshold → alert + prompt refresh cycle. |
| 2.9 | **Cross-Project Learning** | High-scoring pattern extraction, client-detail stripping, shared knowledge base | After each successful project, extract generalizable patterns, anonymize client details, add to shared knowledge. |
| 2.10 | **Specification-Driven Development** | Mandatory spec.md generation, spec completeness scoring (≥8/10), spec storage in Qdrant | Stage 0 of pipeline. Agent generates spec from task description. Review agent scores it. Stored for future retrieval. |

**Exit Criteria:** Agent given a task receives a curated context window (not full repo dump). Context includes relevant code, patterns, anti-patterns, and tool descriptions. Spec phase runs before any code generation.

---

## WAVE 3: SECURITY HARDENING
### *"Every container, every dependency, every secret — locked down"*

**Goal:** Supply chain security, secrets management, threat modeling, runtime protection.
**Duration:** 1.5 weeks
**Prerequisite:** Wave 0 complete

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 3.1 | **Supply Chain Security Suite** | Trivy (containers), Grype+Syft (SBOM), cosign (image signing), OSV-Scanner | Integrated into Build Forge pipeline. Every Docker image scanned, signed, SBOM generated before deployment. |
| 3.2 | **Secret Scanning Pipeline** | gitleaks, detect-secrets, TruffleHog | Pre-commit hooks + pipeline step. Scans all code for leaked secrets, API keys, tokens. |
| 3.3 | **IaC Security Linting** | Hadolint (Dockerfiles), Checkov (IaC), kube-linter (K8s), ShellCheck (scripts) | Pipeline step in Tier 1. All Dockerfiles, docker-compose files, and shell scripts validated. |
| 3.4 | **Threat Modeling Tools** | Threagile, STRIDE-GPT, Threat Dragon | CLI tools available to agents. For every new service, generate threat model. Store in Qdrant. |
| 3.5 | **Runtime Container Security** | Falco (runtime monitoring), Dockle (container best practices), CrowdSec (enhanced) | Falco as daemon on Docker host. Alerts on suspicious container behavior → Mattermost + Omi. |
| 3.6 | **Code Provenance Tracking** | Model attribution per line, prompt attribution, knowledge base influence | Metadata system: every generated file includes provenance header (which model, which prompt version, which knowledge base entries influenced it). |
| 3.7 | **License Compliance Scanner** | ScanCode Toolkit, FOSSA alternative, licensee | Pipeline step. Scans all dependencies for license compatibility. Flags copyleft contamination. |
| 3.8 | **PKI & Certificate Management** | Vault PKI engine, auto-issuance for service-to-service TLS, mTLS enforcement | Vault PKI backend. Every inter-service connection uses mTLS with auto-rotated certificates. |
| 3.9 | **Security-Specific Quality Gate** | npm audit, Safety (Python), cargo-audit (Rust), gosec (Go) | Language-specific security scanners integrated into Tier 2 verification. |
| 3.10 | **LINDDUN Privacy Threat Modeling** | Privacy-specific threat analysis, GDPR compliance patterns | Template for privacy impact assessment. Integrated into spec phase for services handling PII. |
| 3.11 | **Container Hardening** | Read-only filesystems, dropped capabilities, seccomp profiles, non-root users | Docker Compose template updated. All omni-* containers run as non-root with minimal capabilities. |

**Exit Criteria:** `docker scan` passes on all containers. No leaked secrets in any repo. mTLS between all services. SBOM generated for every image.

---

## WAVE 4: KNOWLEDGE ENGINE
### *"Decades of elite engineering knowledge, queryable in milliseconds"*

**Goal:** Populate the 5-layer RAG architecture with elite codebases, academic papers, and patterns across all 30 knowledge categories.
**Duration:** 2.5 weeks
**Prerequisite:** Qdrant operational (System 11/17)

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 4.1 | **Knowledge Ingestion Pipeline** | PDF/MD/HTML document ingestion, chunking, embedding, Qdrant storage | FastAPI service `omni-knowledge-ingestor` (:8360). Takes documents → chunks → embeds (via Ollama) → stores in Qdrant with metadata. |
| 4.2 | **Elite Codebase Ingester** | Linux kernel, PostgreSQL, Redis, SQLite, Chromium patterns | Specialized ingester that clones elite repos, extracts architectural patterns, embeds them with contextual metadata. |
| 4.3 | **Academic Paper Ingester** | Papers across all 30 categories, citation extraction, key finding extraction | Ingests PDFs, extracts key algorithms/patterns/findings, embeds with category metadata. |
| 4.4 | **Design Pattern Library** | 50+ patterns in Neo4j/AGE, language-specific implementations | Graph database of design patterns with relationships (pattern → use case → language implementation → example code). Queryable by agents. |
| 4.5 | **Algorithm Knowledge Module** | Algorithm implementations from Abseil, Folly, crossbeam | Curated collection of elite algorithm implementations, embedded with complexity analysis and use-case metadata. |
| 4.6 | **Platform-Specific Knowledge** | Systems programming, web backend, frontend, mobile (Swift/Kotlin) | Separate Qdrant collections per platform domain. Agents get domain-relevant knowledge based on task type. |
| 4.7 | **Real-World Failure Corpus** | CVE database, post-mortems (Google, AWS, Cloudflare, GitHub, Meta, Stripe), pipeline-caught bugs | Qdrant collection `failure_patterns`. Every failure mode indexed with root cause, detection method, prevention pattern. |
| 4.8 | **Knowledge Freshness Monitor** | RSS feed crawler, GitHub updates, CVE feeds, ArXiv papers | Scheduled service `omni-knowledge-freshness` (:8361). Monitors sources, triggers re-ingestion when content updates. Alerts on stale knowledge. |
| 4.9 | **Framework Documentation Indexer** | Top 20 frameworks (FastAPI, React, Docker, PostgreSQL, etc.), API deprecation flagging | Crawls and indexes official documentation. Flags deprecated APIs that agents might still reference. |
| 4.10 | **GraphRAG Layer** | Knowledge graph relationships, entity extraction, cross-document linking | Neo4j/AGE graph connecting concepts across documents. Enables multi-hop reasoning: "What patterns does PostgreSQL use that are relevant to my cache implementation?" |
| 4.11 | **Incident Knowledge Base** | Post-mortem analysis, conference talks, elite blog posts | Structured database of "what went wrong and why" from elite companies. Agents consult before making architectural decisions. |
| 4.12 | **Knowledge Governance** | Versioning, quality scoring, staleness detection, conflict resolution | Metadata layer tracking knowledge freshness, confidence scores, and source authority. Stale knowledge flagged, not silently served. |
| 4.13 | **Continuous Learning Pipeline** | High-scoring code → training data, feedback loop → knowledge updates | Automated pipeline: successful builds with high review scores → extracted patterns → knowledge base. Failed builds → anti-pattern database. |
| 4.14 | **Conference Talk Ingester** | CppCon, Strange Loop, GOTO, RustConf, USENIX transcripts | Transcripts and slides from elite conferences, chunked and embedded with topic metadata. |

**Exit Criteria:** `omni knowledge stats` shows 100K+ vectors across all collections. Agent given a task retrieves relevant patterns, anti-patterns, and documentation within 200ms.

---

## WAVE 5: CLIENT REVENUE PIPELINE
### *"Intake → Build → Deliver → Invoice — fully automated workflow"*

**Goal:** Complete client-facing workflow from project request to payment collection.
**Duration:** 2 weeks
**Prerequisite:** Waves 0-2 complete

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 5.1 | **Project Intake System** | Request submission (Mattermost, email, web form), project queue, validation | n8n workflow + FastAPI endpoint. Client submits request → parsed → queued → notification to Brendan. |
| 5.2 | **Project Templating Library** | REST API template, Full-stack React+Python template, CLI tool template | 3+ project templates with pre-configured specs, pipeline configs, architecture rules, expected deliverables. Master Orchestrator selects based on task type. |
| 5.3 | **Time Estimation Engine** | Task duration benchmarks, REST API ~45min, full-stack ~3hrs, pricing calculator | Lookup table + ML-based estimation. Historical build data improves estimates over time. Feeds into quote generation. |
| 5.4 | **Quote Generation System** | Pricing calculator, scope document, client-facing estimate | Template that combines time estimate + complexity analysis → professional quote document. |
| 5.5 | **Master Orchestrator Project Init** | Gitea repo creation, Qdrant namespace, task breakdown, Docker network isolation | When project approved: auto-create repo in Gitea, namespace in Qdrant, isolated Docker network, assign to pipeline. |
| 5.6 | **Checkpoint Review System** | Intermediate reviews, preview URLs, client feedback capture | At configurable checkpoints, pause pipeline → generate preview → notify client → capture feedback → resume or iterate. |
| 5.7 | **Final Output Packaging** | Build artifacts, documentation bundle, deployment package | Packages completed project: source code, Docker configs, documentation, deployment scripts, test results. |
| 5.8 | **Client Delivery System** | Handoff mechanism, access provisioning, deployment assistance | Automated delivery: push to client's repo, or provide download package, or deploy to their infrastructure via Coolify. |
| 5.9 | **Automated Invoice Trigger** | Crater integration, time-based billing, project completion trigger | On project completion → generate invoice in Crater → send to client → track payment status. |
| 5.10 | **Multi-Client Data Isolation** | Per-project Qdrant namespaces, Git repos, Docker networks, context separation | Strict isolation. No data leakage between client projects. Each project gets its own namespace, repo, and network. |
| 5.11 | **Client Communication Interface** | Status updates, review requests, delivery notifications | Automated notifications at each pipeline stage. Client can check status via web link. |
| 5.12 | **Client Feedback Loop** | Feedback → Qdrant, satisfaction tracking, improvement signals | All client feedback stored, analyzed, and fed back into knowledge base for continuous improvement. |

**Exit Criteria:** End-to-end test: submit "Build a todo app with user auth" → pipeline runs → preview generated → invoice created. Under 1 hour for simple projects.

---

## WAVE 6: AGENT INTELLIGENCE
### *"Six specialized agents that learn, collaborate, and improve"*

**Goal:** Multi-agent collaboration protocol, prompt optimization, SERA fine-tuning, retrospectives.
**Duration:** 2 weeks
**Prerequisite:** Waves 1-2 complete

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 6.1 | **Agent Role Specialization** | Architect, Developer, Tester, Reviewer, Optimizer, Project Manager roles | Formal role definitions with specialized system prompts, tool access, and knowledge scope per agent. |
| 6.2 | **Multi-Agent Collaboration Protocol** | Handoff protocol, structured inter-agent communication, context passing | JSON-based handoff format. Each agent produces structured output that the next agent consumes. No context lost between agents. |
| 6.3 | **Design Review Agent** | Pre-implementation scoring (10 dimensions), auto-approve if > 8.5/10 | Dedicated agent that evaluates architectural decisions BEFORE code generation. Uses different model from generator. |
| 6.4 | **Code Review Agent** | Post-implementation scoring, structured feedback, fix suggestions | Dedicated agent that reviews generated code. Produces structured JSON scores + natural language feedback. |
| 6.5 | **Security Review Agent** | Threat surface evaluation, security-specific scoring | Specialized agent trained on security patterns. Reviews every change for security implications. |
| 6.6 | **Prompt Engineering Optimization** | promptfoo integration, prompt versioning, A/B testing, automated improvement | promptfoo test suite for all agent prompts. Monthly optimization cycle: test → modify → compare → deploy. Prompt versions tracked with scores. |
| 6.7 | **Post-Task Retrospective System** | Automated retrospective after each task, mistake extraction, prompt updates | After every pipeline run, retrospective agent analyzes what went well/wrong. Findings → knowledge base + prompt refinements. |
| 6.8 | **SERA Automated Fine-Tuning** | Dataset curation, fine-tuning pipeline (Unsloth/Axolotl), model evaluation, promotion | Pipeline: high-quality code accumulates → dataset prepared → fine-tuning job on GPU cloud → evaluate against golden test suite → promote if improved. |
| 6.9 | **Golden Test Suite** | 20-50 representative tasks, known-good outputs, regression detection | Curated set of tasks spanning all complexity levels. Run weekly. Any quality regression → immediate alert. |
| 6.10 | **SWE-bench Integration** | SWE-bench Verified runner, industry-standard benchmarking | Periodic evaluation against SWE-bench to measure system performance against industry baselines. |
| 6.11 | **Agent Configuration A/B Testing** | Compare agent configs, model combinations, prompt variants | Infrastructure to run same task with different configurations and compare quality/speed/cost. |

**Exit Criteria:** Multi-agent pipeline runs with formal handoffs. promptfoo scores tracked. Golden test suite runs weekly with no regressions. SERA fine-tuning pipeline operational.

---

## WAVE 7: ADVANCED TESTING
### *"If it can break, we find it before production does"*

**Goal:** Mutation testing, fuzz testing, chaos engineering, formal verification, contract testing.
**Duration:** 2 weeks
**Prerequisite:** Wave 1 complete

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 7.1 | **Mutation Testing Framework** | mutmut (Python), Stryker (JS/TS), cargo-mutants (Rust), PIT (Java) | Docker image `omni-mutation-tester`. Runs nightly. Reports mutation score. Validates tests actually catch bugs. |
| 7.2 | **Fuzz Testing Suite** | AFL++/libFuzzer (C/C++), Atheris (Python), cargo-fuzz (Rust), jazzer (JVM) | Docker image `omni-fuzzer`. Configurable duration (60s CI, 24h nightly). Crash reports → anti-pattern database. |
| 7.3 | **Property-Based Testing** | Hypothesis (Python), fast-check (TypeScript), proptest (Rust) | Agents generate property tests for functions with mathematical invariants. Integrated into Tier 2 verification. |
| 7.4 | **Chaos Engineering** | Toxiproxy (:8474), Chaos Toolkit | Docker service. Injects network failures, latency, packet loss between services. Validates graceful degradation. |
| 7.5 | **Distributed Systems Testing** | Jepsen (control + 5 nodes), Maelstrom | On-demand Docker cluster. Tests linearizability, serializability of distributed components. |
| 7.6 | **Formal Verification Suite** | TLA+, CBMC, Dafny, Alloy, SPIN | Docker image `omni-formal-verify`. For critical algorithms: model check before implementation. |
| 7.7 | **Symbolic Execution** | KLEE, CrossHair (Python), angr, Kani (Rust) | On-demand analysis. Explores all execution paths. Finds edge cases that unit tests miss. |
| 7.8 | **API Contract Testing** | Pact (consumer-driven), Schemathesis (OpenAPI test generation), Spectral (linting) | Pact broker (:9292). Every API boundary has contract tests. Breaking changes detected pre-deployment. |
| 7.9 | **Visual Regression Testing** | Playwright screenshots, BackstopJS | For frontend projects. Screenshot comparison catches UI regressions. |
| 7.10 | **Database Migration Safety** | squawk (PostgreSQL), schema diff, rollback verification | Every migration analyzed for safety (no locks on large tables, backward compatible). Rollback tested before deploy. |
| 7.11 | **Service Virtualization** | WireMock, Testcontainers, MailHog | Mock external services during testing. MailHog captures all email for verification. |
| 7.12 | **Flaky Test Quarantine** | Flaky test detection, automatic quarantine, periodic retry | Tests that fail intermittently are quarantined, not blocking pipeline. Reported for investigation. |
| 7.13 | **Data Quality Validation** | Pandera (Python), Great Expectations | For data-heavy projects: validate data schemas, completeness, consistency at pipeline boundaries. |

**Exit Criteria:** Mutation score > 80% on all generated code. Fuzz testing runs nightly. Chaos tests validate graceful degradation. Contract tests catch all breaking API changes.

---

## WAVE 8: BUSINESS INFRASTRUCTURE
### *"Everything a commercial AI coding platform needs beyond the code"*

**Goal:** Email, CRM, support, analytics, notifications, webhooks, search — the business layer.
**Duration:** 2.5 weeks
**Prerequisite:** Wave 0 complete

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 8.1 | **Email Infrastructure** | Listmonk (:9001) or Postal for SMTP, transactional + marketing templates, delivery tracking | Docker service. Sends transactional emails (invoice, status update) and marketing (newsletter). No external email service. |
| 8.2 | **Push Notification Service** | Ntfy (:8075), Apprise integration, web push, mobile push | Docker service. Unified notification relay: push to mobile, web, Mattermost, Omi — all from one API. |
| 8.3 | **Customer Support System** | Chatwoot (:3000), AI auto-responses, ticketing, live chat, knowledge base | Docker service. Client-facing support portal. AI agent handles initial triage. Escalates to Brendan for complex issues. |
| 8.4 | **Business Analytics** | PostHog (:8100) or Plausible, feature usage, conversion funnels, cohort analysis | Docker service. Track how clients use delivered products. Privacy-focused, self-hosted. |
| 8.5 | **Webhook Management** | Svix (:8071) or Convoy, signature verification, delivery logs, retry logic | Docker service. Manages all outgoing webhooks with guaranteed delivery, logging, and debugging. |
| 8.6 | **Feature Flags** | Unleash (:4242), SDK integrations, gradual rollouts, kill switches | Docker service. Feature flags for all generated applications. A/B testing support. Emergency kill switches. |
| 8.7 | **Error Tracking** | GlitchTip (:8070), Sentry-compatible, source maps, release tracking | Docker service. Collects errors from all deployed applications. Correlates with Langfuse traces. |
| 8.8 | **Full-Text Search Engine** | Meilisearch (:7700) or Typesense, fuzzy matching, faceted search | Docker service. Powers search across knowledge base, code repos, documentation. Sub-100ms response. |
| 8.9 | **API Gateway** | Kong (:8001) or Tyk, rate limiting, API key management, usage metering | Docker service. Client-facing API gateway with per-customer rate limiting and usage tracking. |
| 8.10 | **Message Queue / Event Bus** | NATS (:4222) or RabbitMQ, event schema registry, dead letter queues | Docker service. Replaces point-to-point HTTP calls for async workflows. Pub/sub for real-time events. |
| 8.11 | **Audit Logging** | Tamper-proof audit trail, compliance reporting (SOC2/HIPAA ready) | Service that logs all system actions immutably. Query interface for compliance reporting. |
| 8.12 | **Form & Survey Builder** | Formbricks (:3005), client intake forms, feedback surveys | Docker service. Powers client intake forms, satisfaction surveys, and onboarding questionnaires. |
| 8.13 | **Scheduling Enhancement** | Cron job manager, CalDAV sync, recurring job management | Enhances Cal.com (System 25) with automated task scheduling, calendar sync, and recurring pipeline jobs. |
| 8.14 | **Real-Time Infrastructure** | Centrifugo (:8300) or Soketi, WebSocket, presence, live collaboration | Docker service. Powers live dashboard updates, real-time pipeline status, collaborative review sessions. |
| 8.15 | **Localization System** | Tolgee (:8085) or Weblate, LibreTranslate, i18n file generation | Docker service. For generated applications that need multi-language support. AI-powered translation suggestions. |

**Exit Criteria:** Client submits request via web form → receives email confirmation → gets real-time status via WebSocket → reviews via Chatwoot → receives invoice via email. Full business workflow operational.

---

## WAVE 9: PERFORMANCE & SCALE
### *"10x faster, 5x cheaper, zero waste"*

**Goal:** Semantic caching, pipeline parallelization, profiling, resource optimization.
**Duration:** 1.5 weeks
**Prerequisite:** Waves 1-2 complete

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 9.1 | **LLM Semantic Caching** | Prompt embedding, Qdrant similarity search, cache hit/miss tracking, 20-40% cost reduction | FastAPI service `omni-semantic-cache` (:8370). Embeds prompts → searches for similar past prompts → returns cached response if similarity > threshold. |
| 9.2 | **Pipeline Parallelization** | Independent stage identification, Woodpecker parallel steps, 40-60% time reduction | Refactor pipeline: Tier 1 checks run in parallel. Tier 2 sub-steps parallelized. Total pipeline time cut by half. |
| 9.3 | **Incremental Analysis** | Changed-files detection, dependency graph traversal, CodeQL incremental DB | Only analyze changed files and their dependents. Skip unchanged code. Massive speedup for iterative development. |
| 9.4 | **Performance Profiling Suite** | py-spy (Python), memray (memory), Valgrind (C/C++), cargo-flamegraph (Rust) | Docker image `omni-profiler`. Available to agents during optimization phase. Flamegraphs → Grafana. |
| 9.5 | **Continuous Benchmarking** | Bencher (:9292), Criterion (Rust), pytest-benchmark, hyperfine | Docker service. Tracks performance benchmarks over time. Regression alerts when code gets slower. |
| 9.6 | **Connection Pooling** | PgBouncer for PostgreSQL, Redis connection pooling | PgBouncer in front of all PostgreSQL instances. Reduces connection overhead across 15+ databases. |
| 9.7 | **Container Resource Optimization** | CPU/memory limits per service, noisy neighbor prevention, resource budgets | Audit all docker-compose files. Set appropriate CPU/memory limits. Prevent any single service from starving others. |
| 9.8 | **Build Caching Intelligence** | ccache/sccache (C/C++/Rust), Turborepo/Nx (JS/TS monorepos) | Cache compilation artifacts. 2-10x faster rebuilds for iterative development. |
| 9.9 | **Cost Tracking Dashboard** | Token consumption, GPU hours, storage, bandwidth — per project | Grafana dashboard aggregating all cost metrics. Monthly budget projections. Per-project cost attribution. |
| 9.10 | **Prompt Cache Optimization** | Stable system prompt prefixes, variable content placement, cache hit rate monitoring | Restructure all agent prompts: static content first (cacheable), dynamic content after. Monitor cache hit rates. |

**Exit Criteria:** Pipeline runs 40% faster. LLM costs reduced 25%+. All services have resource limits. Cost dashboard shows per-project attribution.

---

## WAVE 10: SPECIALIZED CAPABILITIES
### *"Mobile apps, infrastructure-as-code, ML pipelines, media processing"*

**Goal:** Domain-specific toolchains for specialized project types.
**Duration:** 2 weeks
**Prerequisite:** Waves 1-5 complete

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 10.1 | **Mobile Development Toolchain** | Android SDK, React Native/Flutter support, ESLint plugins, mobile profiling, Detox/Maestro testing | Docker image `omni-mobile-dev`. Agents can generate, build, and test mobile apps. Architecture rules enforce mobile best practices. |
| 10.2 | **Infrastructure-as-Code Generation** | Terraform, Kubernetes manifests, Docker Compose, nginx configs, kubeval/kubeconform validation | Agents generate IaC alongside application code. All generated IaC validated with checkov/kubeval before deployment. |
| 10.3 | **ML/AI Quality Pipeline** | MLflow (:5000), DVC (data versioning), experiment tracking, model registry | Docker service. Track ML experiments, version datasets and models, compare runs, register production models. |
| 10.4 | **Media Processing Pipeline** | FFmpeg workers, transcoding queue, thumbnail generation, HLS/DASH streaming | Docker service `omni-media-processor`. For projects requiring video/audio/image processing. |
| 10.5 | **Database Management Suite** | PgBouncer (pooling), CloudBeaver (admin UI), migration runner, schema branching | Enhanced database management. Connection pooling, web-based admin, safe migration execution. |
| 10.6 | **Package/Artifact Repository** | Verdaccio (npm), private PyPI (pypiserver), package scanning | Docker services. Private registries for all generated packages. Vulnerability scanning on upload. |
| 10.7 | **Data Generation & Seeding** | Faker integration, production data anonymizer, realistic test data, demo environment creator | Tools for agents to generate realistic test data. Seed databases for development/demo environments. |
| 10.8 | **Multi-Modal Input Processing** | Vision-capable models (Devstral Small 2, GLM-4.7), image-to-spec conversion | Pipeline accepts image inputs (wireframes, screenshots). Vision model converts to specification. |

**Exit Criteria:** Submit "Build a React Native app with user auth" or "Create a Terraform module for AWS VPC" → pipeline handles it end-to-end with domain-specific tooling.

---

## WAVE 11: POLISH & GOVERNANCE
### *"The last 10% that separates professional from amateur"*

**Goal:** Compliance, internationalization, green engineering, disaster recovery, documentation generation.
**Duration:** 1.5 weeks
**Prerequisite:** Waves 0-8 complete

| # | Build Unit | Items Covered | Deliverable |
|---|-----------|---------------|-------------|
| 11.1 | **Legal & Compliance System** | Legal document templates (ToS, Privacy Policy), GDPR handling, contract management, DSR handler | Template library + n8n workflows. Automated compliance document generation for client projects. |
| 11.2 | **Automated Documentation Generator** | README auto-gen, API docs (OpenAPI), architecture diagrams (Mermaid/D2), runbooks, changelogs | Pipeline stage: after code generation, auto-generate all documentation artifacts. No manual doc writing. |
| 11.3 | **Disaster Recovery System** | Backup verification, point-in-time recovery, off-site replication, DR testing | Enhanced Backup Fortress Pro. Automated DR testing: monthly restore to verify backups work. Off-site replication to VPS. |
| 11.4 | **Green Software Engineering** | Carbon-aware scheduling, resource budgets, efficiency metrics (ops/watt) | Schedule heavy computation during low-demand hours. Track energy efficiency alongside performance. |
| 11.5 | **Accessibility & Compliance** | WCAG 2.1 rules in architecture enforcement, a11y testing in pipeline | For frontend projects: automated accessibility testing. Rules prevent generating inaccessible UIs. |
| 11.6 | **SLO/SLI/SLA Framework** | Mandatory definitions per service, auto-generated from templates | Every generated service includes SLO definitions. SLA tracker (System 29) monitors compliance. |
| 11.7 | **Reproducible Builds** | Nix/Guix for critical components, deterministic dependency resolution | For components requiring bit-for-bit reproducibility. Lock all dependencies to exact versions. |
| 11.8 | **Diagram Generation Pipeline** | Mermaid, PlantUML, D2 — auto-generated from code | Architecture diagrams generated from actual code structure, not manually drawn. Updated on every build. |
| 11.9 | **Protocol & Schema Linting** | buf (protobuf), AsyncAPI CLI, json-schema-validator | For projects using gRPC, event-driven, or schema-heavy architectures. Validate all schemas in pipeline. |

**Exit Criteria:** Every generated project includes: auto-generated docs, architecture diagrams, compliance documents, accessibility-tested UI, SLO definitions, and disaster recovery runbook.

---

## DEPENDENCY MAP

```
Wave 0 ─── Foundation Lock
  │
  ├──→ Wave 1 ─── Verification Core
  │      │
  │      ├──→ Wave 2 ─── Context Intelligence
  │      │      │
  │      │      ├──→ Wave 5 ─── Client Revenue Pipeline (needs Waves 0+1+2)
  │      │      │
  │      │      ├──→ Wave 6 ─── Agent Intelligence (needs Waves 1+2)
  │      │      │
  │      │      └──→ Wave 9 ─── Performance & Scale (needs Waves 1+2)
  │      │
  │      ├──→ Wave 7 ─── Advanced Testing (needs Wave 1)
  │      │
  │      └──→ Wave 10 ── Specialized Capabilities (needs Waves 1+5)
  │
  ├──→ Wave 3 ─── Security Hardening (needs Wave 0)
  │
  ├──→ Wave 4 ─── Knowledge Engine (needs Wave 0, Qdrant)
  │
  ├──→ Wave 8 ─── Business Infrastructure (needs Wave 0)
  │
  └──→ Wave 11 ── Polish & Governance (needs Waves 0-8)
```

**Critical Path:** Wave 0 → Wave 1 → Wave 2 → Wave 5 (first revenue capability)

**Parallel Tracks (can run simultaneously):**
- Track A: Wave 0 → 1 → 2 → 5 → 6 → 9 (core AI pipeline)
- Track B: Wave 0 → 3 (security, runs parallel to Wave 1)
- Track C: Wave 0 → 4 (knowledge, runs parallel to Waves 1-2)
- Track D: Wave 0 → 8 (business, runs parallel to Waves 1-3)

---

## HARDWARE REQUIREMENTS BY WAVE

| Wave | Additional RAM | Additional Storage | GPU Needed |
|------|---------------|-------------------|------------|
| 0 | +16 GB (for Systems 29-37) | +50 GB | No (except Ollama) |
| 1 | +8 GB (CodeQL, Infer are memory-hungry) | +20 GB | No |
| 2 | +4 GB (Context compiler, MCP servers) | +10 GB | No |
| 3 | +2 GB (Falco, scanners) | +5 GB | No |
| 4 | +16 GB (embedding computation) | +200 GB (knowledge base) | Yes (embedding generation) |
| 5 | +2 GB (workflow services) | +5 GB | No |
| 6 | +4 GB (additional agents) | +10 GB | Yes (fine-tuning) |
| 7 | +8 GB (Jepsen cluster, fuzzers) | +20 GB | No |
| 8 | +24 GB (15+ new services) | +50 GB | No |
| 9 | +2 GB (caching layer) | +20 GB (cache storage) | No |
| 10 | +8 GB (ML tools, media processing) | +30 GB | Yes (ML training) |
| 11 | +2 GB (compliance tools) | +5 GB | No |
| **TOTAL** | **~96 GB additional** | **~425 GB** | **Intermittent** |

**Minimum hardware for full deployment:** 128 GB RAM, 2 TB NVMe, 32 CPU cores, 80 GB VRAM GPU

---

## NEW DOCKER SERVICES REGISTRY (Beyond Core 37)

| Service | Container Name | Port | Wave | Priority |
|---------|---------------|------|------|----------|
| Code Scorer | omni-code-scorer | 8350 | 1 | HIGH |
| Gate Engine | omni-gate-engine | 8351 | 1 | HIGH |
| Sourcegraph | omni-sourcegraph | 7080 | 1 | HIGH |
| Context Compiler | omni-context-compiler | 8325 | 2 | HIGH |
| Knowledge Ingestor | omni-knowledge-ingestor | 8360 | 4 | HIGH |
| Knowledge Freshness | omni-knowledge-freshness | 8361 | 4 | STANDARD |
| Semantic Cache | omni-semantic-cache | 8370 | 9 | HIGH |
| Listmonk (Email) | omni-listmonk | 9001 | 8 | STANDARD |
| Ntfy (Notifications) | omni-ntfy | 8075 | 8 | STANDARD |
| Chatwoot (Support) | omni-chatwoot | 3000 | 8 | STANDARD |
| PostHog (Analytics) | omni-posthog | 8100 | 8 | STANDARD |
| Svix (Webhooks) | omni-svix | 8071 | 8 | STANDARD |
| Unleash (Feature Flags) | omni-unleash | 4242 | 8 | STANDARD |
| GlitchTip (Errors) | omni-glitchtip | 8070 | 8 | STANDARD |
| Meilisearch (Search) | omni-meilisearch | 7700 | 8 | STANDARD |
| NATS (Event Bus) | omni-nats | 4222 | 8 | HIGH |
| Centrifugo (WebSocket) | omni-centrifugo | 8300 | 8 | STANDARD |
| Formbricks (Forms) | omni-formbricks | 3005 | 8 | STANDARD |
| Tolgee (i18n) | omni-tolgee | 8085 | 8 | STANDARD |
| Pact Broker | omni-pact-broker | 9292 | 7 | STANDARD |
| Toxiproxy (Chaos) | omni-toxiproxy | 8474 | 7 | STANDARD |
| MLflow (ML Tracking) | omni-mlflow | 5000 | 10 | STANDARD |
| Verdaccio (npm) | omni-verdaccio | 4873 | 10 | STANDARD |
| Bencher (Benchmarks) | omni-bencher | 9293 | 9 | STANDARD |
| CloudBeaver (DB Admin) | omni-cloudbeaver | 8978 | 10 | STANDARD |

**Total new services: ~25** (bringing platform total to ~95 services)

---

## QUICK START: WHAT TO BUILD FIRST

If you want to start generating revenue as fast as possible, follow this abbreviated path:

### MINIMUM VIABLE PLATFORM (4 weeks)

1. **Week 1:** Wave 0 (Foundation Lock) — boot script, .env, Systems 29-37
2. **Week 2:** Wave 1 items 1.1-1.6 (Verification tiers 1-3, scoring, gates)
3. **Week 3:** Wave 2 items 2.1, 2.7, 2.10 (Context compiler, anti-patterns, spec-driven dev)
4. **Week 4:** Wave 5 items 5.1-5.5, 5.9 (Intake, templates, time estimates, project init, invoicing)

**Result after 4 weeks:** Client submits request → spec generated → code generated → verified through 3 tiers → scored → delivered → invoiced. The full autonomous pipeline.

### THEN ITERATE

- Week 5-6: Wave 3 (security) + Wave 4 starts (knowledge ingestion begins)
- Week 7-8: Wave 6 (agent intelligence) + Wave 4 continues
- Week 9-10: Wave 7 (advanced testing) + Wave 8 starts (business infra)
- Week 11-12: Wave 9 (performance) + Wave 8 continues
- Week 13+: Waves 10-11 (specialized + polish)

---

## TRACKING & GOVERNANCE

### How to Track Progress

Each Build Unit becomes a card in your Notion kanban board:
- **Backlog** → **In Progress** → **Testing** → **Deployed** → **Verified**
- Each card links to its Docker Compose, config files, and test results
- Weekly review: run golden test suite, check pipeline stats, review cost dashboard

### Definition of Done (Per Build Unit)

1. Docker Compose with health checks, labels, logging ✅
2. Config files (all secrets from Vault, not hardcoded) ✅
3. Integration with omni-quantum-network ✅
4. Prometheus metrics exposed ✅
5. Grafana dashboard created ✅
6. Mattermost notification configured ✅
7. Omi alert for critical events ✅
8. Backup included in schedule ✅
9. README with usage examples ✅
10. Master Orchestrator aware of new service ✅

---

*This document is the single source of truth for Omni Quantum Elite build execution. Every item from the 843-item audit is accounted for. Nothing is lost. Everything has a home.*

**Build the future. One wave at a time.** ⚛
