# Omni Quantum Elite AI Coding System — The Final Twelve Dimensions

## What This Document Is

You've built an extraordinary system across four phases:

- **Phase 1 (v3.0):** 6 agents, 3-tier LLM stack, 5-layer knowledge architecture, 8-stage pipeline, 26 Docker services
- **Phase 2 (Gap Analysis):** +13 systems → code coverage, fuzzing, MCP servers, CodeQL, sanitizers, Infer, Sourcegraph, scoring, architecture enforcement, benchmarking, ADRs, AST refactoring, Jepsen simulation
- **Phase 3 (Next-Level):** +24 enhancements → formal verification, mutation testing, symbolic execution, API contracts, profiling, chaos engineering, complexity metrics, supply chain security, OPA policies, migration safety, semver, runtime validation, git hygiene, doc-as-tests, flaky test detection, canary deployment, error tracking, feature flags, Nix, visual regression, diagrams, protocol linting, build caching
- **Phase 4 (Strategic):** +28 strategic capabilities → agent intelligence (spec-driven, design review, multi-agent collaboration, self-evaluation, prompt optimization), knowledge deepening (algorithms, patterns, platform modules, freshness, anti-patterns), missing tools (threat modeling, IaC quality, secrets, observability, service virtualization, data validation, tech debt), architectural patterns (12-factor, DDD, error handling), operational excellence (SLOs, incident response, post-incident learning, cost-aware engineering), emerging paradigms (Wasm, ML/AI quality, privacy, green software)

**That's ~110+ tools, 50+ Docker services, 30+ pipeline sub-stages, 12 knowledge domains.**

This document identifies **12 dimensions that remain genuinely untouched** — not more tools or quality gates, but fundamental system capabilities that elite engineering organizations (Apple, Google, Meta, Stripe) have and your system currently lacks. These are the structural gaps between "a powerful collection of tools" and "an autonomous engineering organization."

---

# DIMENSION 1: THE CONTROL PLANE — How You Actually Use This System

**The Problem:** You have 50+ Docker services, 8 pipeline stages, 6 agents, and 110+ tools. But there's no unified interface for submitting work, monitoring progress, approving outputs, or managing projects. Right now, interacting with this system likely means SSH, terminal commands, and reading logs. That's not how Apple's engineering teams operate.

**What Elite Organizations Have:** A unified developer portal. Google has an internal tool called Cider/CitC. Spotify built Backstage. Meta has their internal developer experience platform. These aren't just dashboards — they're the nervous system that connects humans to automation.

## 1A. Project Intake & Request System

Every piece of work should start with a structured request:

```yaml
# project-request.yaml — submitted via web UI or API
project:
  name: "invoice-microservice"
  type: "new-service"  # new-service | feature | bugfix | refactor | migration
  priority: "high"
  requester: "brendan"
  
description: |
  Build a FastAPI microservice that processes invoices from PDF uploads,
  extracts line items via OCR, validates against vendor database, and
  stores in PostgreSQL with full audit trail.

constraints:
  languages: ["python"]
  frameworks: ["fastapi", "sqlalchemy"]
  databases: ["postgresql"]
  must_integrate_with: ["omni-invoice-engine", "omni-tax-fortress"]
  deployment_target: "docker-compose"
  
acceptance_criteria:
  - "PDF upload endpoint accepts multipart/form-data"
  - "Line item extraction accuracy >95% on test corpus"
  - "Full CRUD API with OpenAPI documentation"
  - "99.9% uptime SLO"
  
deadline: "2026-02-15"
token_budget: "medium"  # low: 50K tokens | medium: 200K | high: 1M | unlimited
```

### Docker Service: omni-control-plane

```yaml
# docker-compose.control-plane.yml
services:
  omni-control-plane:
    image: node:20-slim
    container_name: omni-control-plane
    labels:
      - "omni.system=control-plane"
      - "omni.tier=core"
    ports:
      - "8300:3000"
    volumes:
      - ./control-plane:/app
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - DATABASE_URL=postgresql://omni:omni@omni-postgres:5432/control_plane
      - MATTERMOST_WEBHOOK_URL=${MATTERMOST_WEBHOOK_URL}
      - REDIS_URL=redis://omni-redis:6379/5
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

### Technology Stack (All Open Source, Self-Hosted)

| Component | Tool | License | Purpose |
|-----------|------|---------|---------|
| Web Framework | Next.js or SvelteKit | MIT | Dashboard UI |
| API Layer | FastAPI | MIT | REST/WebSocket API |
| Task Queue | BullMQ (Redis-backed) | MIT | Job orchestration |
| Real-Time | Socket.IO | MIT | Live pipeline updates |
| Database | PostgreSQL | PostgreSQL License | Project/job state |
| Auth | Authentik or Keycloak | MIT/Apache-2.0 | SSO, RBAC |

### What the Dashboard Shows

**Project Board View:**
- All active projects with status (queued → spec → design-review → coding → testing → review → staging → complete)
- Per-project token consumption and cost estimate
- Agent assignment and current activity
- Pipeline stage progress with real-time logs

**Pipeline Visualization:**
- Directed acyclic graph of all pipeline stages
- Green/yellow/red status per stage
- Click-to-expand for stage logs, tool outputs, and metrics
- Time-per-stage trending

**Agent Activity Monitor:**
- Which agent is working on what
- Current context window utilization
- Token consumption rate
- Quality score trending per agent

**Knowledge Base Status:**
- Qdrant collection sizes and freshness
- Neo4j graph statistics
- Last knowledge ingestion timestamp
- Knowledge coverage heat map by domain

## 1B. Human-in-the-Loop Approval Gates

Elite organizations never ship without human review. Your system needs configurable gates:

```yaml
# approval-gates.yaml
gates:
  spec_approval:
    stage: "after-spec-generation"
    type: "mandatory"  # mandatory | optional | auto-approve-if-score-above
    auto_approve_threshold: null  # null = always require human
    notify: ["mattermost", "omi-haptic"]
    timeout_hours: 48
    
  design_review:
    stage: "after-design-review"
    type: "auto-approve-if-score-above"
    auto_approve_threshold: 8.5  # out of 10
    notify: ["mattermost"]
    timeout_hours: 24
    
  code_review:
    stage: "after-pipeline-complete"
    type: "mandatory"
    notify: ["mattermost", "omi-haptic"]
    timeout_hours: 72
    
  deployment:
    stage: "before-production-deploy"
    type: "mandatory"
    require_all_tests_pass: true
    require_security_scan_clean: true
    notify: ["mattermost", "omi-haptic"]
```

### Approval UI Workflow

1. Agent completes a stage → notification to Mattermost with summary
2. Brendan opens dashboard → sees approval request with full context
3. Can view: generated spec, design review scores, generated code (diff view), all test results, security scan results, pipeline metrics
4. Actions: **Approve** (proceed to next stage), **Request Changes** (with comments — fed back to agent as instructions), **Reject** (kill project with reason — fed to anti-pattern database)
5. Agent receives feedback → incorporates → resubmits for approval

### Feedback Learning

Every approval/rejection/revision becomes training data:

```python
# feedback_collector.py
def record_feedback(project_id: str, stage: str, decision: str, comments: str):
    feedback = {
        "project_id": project_id,
        "stage": stage,
        "decision": decision,  # approved | revision_requested | rejected
        "comments": comments,
        "generated_output_hash": hash_output(project_id, stage),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Store in Qdrant for RAG retrieval
    embed_and_store(
        collection="human_feedback",
        text=f"Stage: {stage}. Decision: {decision}. Feedback: {comments}",
        metadata=feedback
    )
    
    # If revision requested, extract patterns
    if decision == "revision_requested":
        extract_revision_patterns(feedback)
    
    # If rejected, add to anti-pattern database
    if decision == "rejected":
        add_to_antipatterns(feedback)
```

---

# DIMENSION 2: SYSTEM SELF-ASSURANCE — Testing the Tester

**The Problem:** You have exhaustive quality gates for generated code — but who tests the AI coding system itself? If you update a prompt, swap an LLM model, upgrade a tool version, or change pipeline ordering, how do you know the system still produces good code? You're testing the output but not the machine that produces the output.

**What Elite Organizations Have:** Google tests their build system with the build system. Facebook's test infrastructure has its own test suite. The testing framework is itself tested.

## 2A. Golden Test Suites (Regression Testing for the Pipeline)

A "golden test" is a known-good input/output pair. You feed the system a specification and verify the output matches (or exceeds) a baseline.

```yaml
# golden-tests/manifest.yaml
golden_tests:
  - id: "GT-001"
    name: "Simple REST API"
    description: "FastAPI CRUD service with PostgreSQL"
    input_spec: "golden-tests/specs/simple-rest-api.md"
    expected_outputs:
      - file: "main.py"
        must_contain: ["FastAPI", "SQLAlchemy", "Pydantic"]
        must_not_contain: ["print(", "TODO", "pass  #"]
      - file: "Dockerfile"
        must_pass: ["hadolint", "checkov"]
      - file: "tests/"
        min_coverage: 80
    quality_gates:
      min_pipeline_score: 7.5
      max_critical_findings: 0
      max_high_findings: 2
    baseline_metrics:
      pipeline_duration_seconds: 180
      token_consumption: 45000
      
  - id: "GT-002"
    name: "Event-Driven Microservice"
    description: "Async service with Redis Streams, retry logic, DLQ"
    input_spec: "golden-tests/specs/event-driven-service.md"
    expected_outputs:
      - file: "main.py"
        must_contain: ["asyncio", "redis", "dead_letter"]
      - file: "docker-compose.yml"
        must_pass: ["docker-compose config"]
    quality_gates:
      min_pipeline_score: 8.0
      max_critical_findings: 0
    
  - id: "GT-003"
    name: "CLI Tool with Plugin Architecture"
    description: "Click-based CLI with pluggable commands"
    input_spec: "golden-tests/specs/cli-tool.md"
    expected_outputs:
      - file: "cli.py"
        must_contain: ["click", "plugin", "entry_points"]
      
  # ... 20+ golden tests covering diverse project types
```

### Running Golden Tests

```bash
#!/bin/bash
# run_golden_tests.sh — Run after any system change
# (prompt update, model swap, tool upgrade, pipeline change)

RESULTS_DIR="golden-test-results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

for test in golden-tests/specs/*.md; do
    test_id=$(basename "$test" .md)
    echo "Running golden test: $test_id"
    
    # Submit to pipeline
    omni-cli submit \
        --spec "$test" \
        --mode "golden-test" \
        --output-dir "$RESULTS_DIR/$test_id" \
        --timeout 600
    
    # Validate outputs against manifest
    omni-cli validate \
        --manifest golden-tests/manifest.yaml \
        --test-id "$test_id" \
        --actual "$RESULTS_DIR/$test_id" \
        --report "$RESULTS_DIR/$test_id/report.json"
done

# Generate comparison report
omni-cli golden-report \
    --results "$RESULTS_DIR" \
    --baseline "golden-test-results/baseline" \
    --output "$RESULTS_DIR/comparison.html"

# Alert if regression detected
if grep -q '"regression": true' "$RESULTS_DIR"/*/report.json; then
    notify_mattermost "⚠️ Golden test regression detected. Review: $RESULTS_DIR"
fi
```

## 2B. Agent Output Benchmarking (SWE-bench / HumanEval)

Measure your system against industry-standard benchmarks:

```yaml
# benchmarks/config.yaml
benchmarks:
  swe_bench:
    description: "Real-world GitHub issue resolution"
    dataset: "princeton-nlp/SWE-bench_Lite"  # 300 curated issues
    frequency: "weekly"
    metrics: ["resolve_rate", "avg_tokens", "avg_duration"]
    target_resolve_rate: 0.45  # top commercial agents hit ~0.40-0.50
    
  humaneval:
    description: "Function-level code generation"
    dataset: "openai/humaneval"
    frequency: "after-model-change"
    metrics: ["pass@1", "pass@5"]
    target_pass_at_1: 0.85
    
  mbpp:
    description: "Mostly Basic Python Problems"
    dataset: "google-research/mbpp"
    frequency: "after-model-change"
    metrics: ["pass@1"]
    target_pass_at_1: 0.80
    
  custom_elite:
    description: "Custom benchmark matching your project types"
    dataset: "golden-tests/benchmark-suite/"
    frequency: "weekly"
    metrics: ["quality_score", "security_score", "architecture_score"]
```

### Trending Dashboard

Track these metrics over time. Every model swap, prompt change, or pipeline modification should show up in the trend line. If pass@1 drops from 0.85 to 0.78 after a prompt change, you immediately see it and can revert.

## 2C. A/B Testing Agent Configurations

```python
# ab_test_runner.py
import random
from dataclasses import dataclass

@dataclass
class AgentConfig:
    name: str
    model: str
    system_prompt_version: str
    temperature: float
    max_tokens: int
    tools_enabled: list[str]

config_a = AgentConfig(
    name="baseline",
    model="devstral-2-123b",
    system_prompt_version="v2.4",
    temperature=0.1,
    max_tokens=8192,
    tools_enabled=["search", "execute", "lint"]
)

config_b = AgentConfig(
    name="experimental",
    model="qwen3-coder-235b",
    system_prompt_version="v2.5-experimental",
    temperature=0.05,
    max_tokens=16384,
    tools_enabled=["search", "execute", "lint", "verify"]
)

def run_ab_test(spec_path: str, num_trials: int = 10):
    results = {"a": [], "b": []}
    
    for i in range(num_trials):
        config = random.choice([config_a, config_b])
        group = "a" if config == config_a else "b"
        
        result = run_pipeline(spec_path, config)
        results[group].append({
            "quality_score": result.quality_score,
            "tokens_used": result.tokens_used,
            "duration_seconds": result.duration_seconds,
            "test_pass_rate": result.test_pass_rate,
            "security_findings": result.security_findings
        })
    
    return statistical_comparison(results["a"], results["b"])
```

---

# DIMENSION 3: CONTEXT ENGINEERING — The 200K Token Challenge

**The Problem:** Your agents will routinely work on codebases with hundreds of files. No LLM can hold an entire codebase in its context window. The quality of generated code is directly proportional to the quality of context selection. This is arguably the single highest-leverage improvement you can make. A mediocre model with perfect context will outperform a brilliant model with garbage context.

**What Elite Organizations Have:** Google's internal code search (Kythe) maintains a complete index of billions of lines. Meta's Aroma uses ML for code recommendation. Apple's Xcode has deep project-wide understanding.

## 3A. Codebase Indexing & Semantic Search

Every project managed by the system should be indexed for retrieval:

```yaml
# docker-compose.code-index.yml
services:
  omni-code-index:
    image: python:3.12-slim
    container_name: omni-code-index
    labels:
      - "omni.system=code-index"
      - "omni.tier=core"
    ports:
      - "8310:8000"
    volumes:
      - ./code-index:/app
      - ./projects:/projects:ro
    environment:
      - QDRANT_URL=http://omni-qdrant:6333
      - COLLECTION_NAME=codebase_index
      - EMBEDDING_MODEL=nomic-embed-code  # code-specific embeddings
    networks:
      - omni-quantum-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
    restart: unless-stopped
```

### Indexing Strategy

```python
# code_indexer.py — Index codebases for semantic retrieval

import tree_sitter_languages
from pathlib import Path

def index_codebase(project_path: str, qdrant_client, collection: str):
    """Index a codebase at multiple granularity levels."""
    
    # Level 1: File-level summaries
    for file_path in iter_source_files(project_path):
        content = file_path.read_text()
        summary = generate_file_summary(content, file_path.name)
        embed_and_store(qdrant_client, collection, {
            "level": "file",
            "path": str(file_path.relative_to(project_path)),
            "summary": summary,
            "language": detect_language(file_path),
            "imports": extract_imports(content),
            "exports": extract_exports(content),
            "loc": len(content.splitlines())
        })
    
    # Level 2: Function/class-level chunks (AST-aware)
    for file_path in iter_source_files(project_path):
        language = detect_language(file_path)
        parser = tree_sitter_languages.get_parser(language)
        tree = parser.parse(file_path.read_bytes())
        
        for node in extract_definitions(tree.root_node):
            chunk = file_path.read_text()[node.start_byte:node.end_byte]
            embed_and_store(qdrant_client, collection, {
                "level": "definition",
                "path": str(file_path.relative_to(project_path)),
                "name": node.name,
                "type": node.type,  # function, class, method
                "signature": extract_signature(node),
                "docstring": extract_docstring(node),
                "content": chunk,
                "dependencies": extract_dependencies(node)
            })
    
    # Level 3: Dependency graph
    dep_graph = build_dependency_graph(project_path)
    for module, deps in dep_graph.items():
        embed_and_store(qdrant_client, collection, {
            "level": "dependency",
            "module": module,
            "imports_from": deps["imports"],
            "imported_by": deps["imported_by"],
            "coupling_score": calculate_coupling(module, dep_graph)
        })
    
    # Level 4: Architecture summary
    arch_summary = generate_architecture_summary(project_path, dep_graph)
    embed_and_store(qdrant_client, collection, {
        "level": "architecture",
        "summary": arch_summary,
        "modules": list(dep_graph.keys()),
        "patterns_detected": detect_patterns(dep_graph)
    })
```

## 3B. Intelligent Context Selection

When an agent needs to work on a task, the context assembler decides what goes into the prompt:

```python
# context_assembler.py — The most important file in the entire system

class ContextAssembler:
    """Assembles optimal context for agent tasks within token budget."""
    
    def __init__(self, max_tokens: int = 128_000, reserved_tokens: int = 16_000):
        self.max_tokens = max_tokens
        self.available_tokens = max_tokens - reserved_tokens  # reserve for output
        
    def assemble(self, task: Task, project: Project) -> str:
        """Build context in priority order, filling until budget exhausted."""
        
        context_blocks = []
        tokens_used = 0
        
        # Priority 1: Task specification (always included)
        spec_block = self.format_spec(task.specification)
        tokens_used += count_tokens(spec_block)
        context_blocks.append(("spec", spec_block))
        
        # Priority 2: Directly referenced files
        for file_path in task.referenced_files:
            content = project.read_file(file_path)
            block = f"### File: {file_path}\n```\n{content}\n```"
            if tokens_used + count_tokens(block) < self.available_tokens:
                tokens_used += count_tokens(block)
                context_blocks.append(("referenced", block))
        
        # Priority 3: Files semantically similar to the task
        similar_files = self.semantic_search(
            query=task.description,
            collection="codebase_index",
            filter={"level": "definition"},
            limit=20
        )
        for result in similar_files:
            block = f"### Related: {result.path} ({result.name})\n```\n{result.content}\n```"
            if tokens_used + count_tokens(block) < self.available_tokens * 0.6:
                tokens_used += count_tokens(block)
                context_blocks.append(("semantic", block))
        
        # Priority 4: Relevant knowledge from RAG
        knowledge = self.knowledge_search(
            query=task.description,
            collections=["algorithms", "design_patterns", "anti_patterns"],
            limit=5
        )
        for item in knowledge:
            block = f"### Knowledge: {item.title}\n{item.content}"
            if tokens_used + count_tokens(block) < self.available_tokens * 0.75:
                tokens_used += count_tokens(block)
                context_blocks.append(("knowledge", block))
        
        # Priority 5: Architecture context
        arch = project.get_architecture_summary()
        block = f"### Project Architecture\n{arch}"
        if tokens_used + count_tokens(block) < self.available_tokens * 0.85:
            tokens_used += count_tokens(block)
            context_blocks.append(("architecture", block))
        
        # Priority 6: Relevant ADRs
        adrs = self.search_adrs(task.description, limit=3)
        for adr in adrs:
            block = f"### ADR: {adr.title}\nDecision: {adr.decision}\nContext: {adr.context}"
            if tokens_used + count_tokens(block) < self.available_tokens * 0.90:
                tokens_used += count_tokens(block)
                context_blocks.append(("adr", block))
        
        # Priority 7: Recent feedback on similar tasks
        feedback = self.search_feedback(task.description, limit=3)
        for fb in feedback:
            block = f"### Past Feedback: {fb.decision}\n{fb.comments}"
            if tokens_used + count_tokens(block) < self.available_tokens * 0.95:
                tokens_used += count_tokens(block)
                context_blocks.append(("feedback", block))
        
        # Log context composition for analysis
        self.log_context_composition(task.id, context_blocks, tokens_used)
        
        return self.format_final_context(context_blocks)
```

### Context Quality Metrics

Track whether context selection is improving code quality:

```python
# context_metrics.py
def analyze_context_effectiveness(task_id: str):
    """After task completion, correlate context composition with output quality."""
    
    context_log = load_context_log(task_id)
    pipeline_results = load_pipeline_results(task_id)
    
    return {
        "task_id": task_id,
        "total_context_tokens": context_log["tokens_used"],
        "context_composition": {
            category: sum(count_tokens(b) for cat, b in context_log["blocks"] if cat == category)
            for category in ["spec", "referenced", "semantic", "knowledge", "architecture", "adr", "feedback"]
        },
        "output_quality_score": pipeline_results["quality_score"],
        "tests_pass_rate": pipeline_results["test_pass_rate"],
        "security_findings": pipeline_results["security_findings"],
        
        # Key question: which context blocks actually influenced the output?
        "context_utilization": estimate_context_utilization(context_log, pipeline_results)
    }
```

---

# DIMENSION 4: DELIVERY & PRODUCTION OPERATIONS

**The Problem:** Your pipeline generates code and validates it — but the story ends there. How does generated code get deployed? How do you manage dev/staging/production environments? How do you handle zero-downtime deployments? The pipeline's last mile — from "code passed all gates" to "running in production" — is entirely missing.

**What Elite Organizations Have:** Fully automated deployment pipelines with progressive rollouts, automated rollbacks, traffic shifting, and health-based promotion.

## 4A. Deployment Pipeline (Post-Code-Generation)

```yaml
# deployment-pipeline.yaml — Extends the 8-stage coding pipeline
deployment_stages:
  stage_9_build:
    name: "Container Build & Scan"
    steps:
      - name: "Docker Build"
        command: "docker build -t ${PROJECT_NAME}:${GIT_SHA} ."
        
      - name: "Container Scan"
        command: "trivy image --severity HIGH,CRITICAL ${PROJECT_NAME}:${GIT_SHA}"
        fail_on: "HIGH,CRITICAL"
        
      - name: "SBOM Generation"
        command: "syft ${PROJECT_NAME}:${GIT_SHA} -o spdx-json > sbom.json"
        
      - name: "Image Sign"
        command: "cosign sign --key cosign.key ${REGISTRY}/${PROJECT_NAME}:${GIT_SHA}"
  
  stage_10_staging:
    name: "Staging Deployment"
    approval_gate: false  # auto-deploy to staging
    steps:
      - name: "Deploy to Staging"
        command: "docker-compose -f docker-compose.staging.yml up -d"
        
      - name: "Smoke Tests"
        command: "pytest tests/smoke/ --base-url=http://staging:8000"
        timeout: 120
        
      - name: "Integration Tests (Against Staging)"
        command: "pytest tests/integration/ --base-url=http://staging:8000"
        timeout: 300
        
      - name: "Load Test (Baseline)"
        command: |
          k6 run --out json=load-results.json \
            -e BASE_URL=http://staging:8000 \
            tests/load/baseline.js
        thresholds:
          p95_response_time_ms: 500
          error_rate: 0.01
  
  stage_11_production:
    name: "Production Deployment"
    approval_gate: true  # ALWAYS require human approval for production
    strategy: "blue-green"  # blue-green | canary | rolling
    steps:
      - name: "Pre-Deploy Health Check"
        command: "curl -f http://production:8000/health"
        
      - name: "Deploy (Blue-Green)"
        command: |
          # Deploy new version as 'green'
          docker-compose -f docker-compose.prod.yml up -d --no-deps ${SERVICE_NAME}-green
          # Wait for health
          wait_for_healthy ${SERVICE_NAME}-green 60
          # Switch traffic
          update_traefik_routing ${SERVICE_NAME} green
          # Drain old 'blue'
          sleep 30
          docker-compose -f docker-compose.prod.yml stop ${SERVICE_NAME}-blue
          
      - name: "Post-Deploy Verification"
        command: "pytest tests/smoke/ --base-url=http://production:8000"
        
      - name: "Monitor (5 min window)"
        command: |
          monitor_error_rate ${SERVICE_NAME} 300 \
            --threshold 0.01 \
            --rollback-on-breach
```

## 4B. Environment Management

```yaml
# environments.yaml — Generated alongside every project
environments:
  development:
    compose_file: "docker-compose.dev.yml"
    variables:
      DATABASE_URL: "postgresql://dev:dev@localhost:5432/dev_db"
      LOG_LEVEL: "DEBUG"
      ENABLE_CORS: "true"
      ENABLE_SWAGGER: "true"
    resources:
      memory_limit: "512m"
      cpu_limit: "0.5"
      
  staging:
    compose_file: "docker-compose.staging.yml"
    variables:
      DATABASE_URL: "postgresql://staging:${STAGING_DB_PASS}@omni-postgres:5432/staging_db"
      LOG_LEVEL: "INFO"
      ENABLE_CORS: "false"
      ENABLE_SWAGGER: "true"
    resources:
      memory_limit: "1g"
      cpu_limit: "1.0"
    monitoring:
      error_tracking: true
      tracing_sample_rate: 1.0  # 100% in staging
      
  production:
    compose_file: "docker-compose.prod.yml"
    variables:
      DATABASE_URL: "postgresql://prod:${PROD_DB_PASS}@omni-postgres:5432/prod_db"
      LOG_LEVEL: "WARNING"
      ENABLE_CORS: "false"
      ENABLE_SWAGGER: "false"
    resources:
      memory_limit: "2g"
      cpu_limit: "2.0"
    monitoring:
      error_tracking: true
      tracing_sample_rate: 0.1  # 10% in production
    rollback:
      automatic: true
      error_rate_threshold: 0.05
      latency_p99_threshold_ms: 2000
```

## 4C. Rollback & Disaster Recovery

```python
# rollback_manager.py
class RollbackManager:
    """Automated rollback when production metrics breach thresholds."""
    
    def __init__(self, prometheus_url: str, service_name: str):
        self.prometheus = PrometheusClient(prometheus_url)
        self.service = service_name
        self.deployment_history = []
    
    def monitor_deployment(self, new_version: str, window_seconds: int = 300):
        """Monitor a new deployment for the observation window."""
        start = time.time()
        
        while time.time() - start < window_seconds:
            metrics = self.prometheus.query({
                "error_rate": f'rate(http_requests_total{{service="{self.service}",status=~"5.."}}[1m])',
                "p99_latency": f'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{self.service}"}}[1m]))',
                "active_connections": f'http_active_connections{{service="{self.service}"}}'
            })
            
            if metrics["error_rate"] > 0.05:
                self.execute_rollback(reason=f"Error rate {metrics['error_rate']:.2%} > 5%")
                return False
                
            if metrics["p99_latency"] > 2.0:
                self.execute_rollback(reason=f"P99 latency {metrics['p99_latency']:.1f}s > 2s")
                return False
            
            time.sleep(10)
        
        # Observation window passed — deployment is healthy
        self.promote_deployment(new_version)
        return True
    
    def execute_rollback(self, reason: str):
        """Roll back to the previous known-good version."""
        previous = self.deployment_history[-1]
        
        notify_mattermost(f"🔴 Auto-rollback for {self.service}: {reason}")
        notify_omi_haptic("urgent")
        
        # Switch traffic back to previous version
        switch_traffic(self.service, previous["version"])
        
        # Record incident for post-incident learning
        record_incident({
            "service": self.service,
            "type": "auto-rollback",
            "reason": reason,
            "rolled_back_version": self.current_version,
            "restored_version": previous["version"],
            "timestamp": datetime.utcnow().isoformat()
        })
```

---

# DIMENSION 5: DOCUMENTATION GENERATION INTELLIGENCE

**The Problem:** Elite code ships with elite documentation. Your system generates code, tests, Dockerfiles, and configurations — but not documentation. No README, no API docs, no architecture diagrams, no user guides, no deployment instructions.

**What Elite Organizations Have:** Documentation is generated alongside code, validated for accuracy, and treated as a first-class artifact.

## 5A. Mandatory Documentation Artifacts

Every project the system generates must include these:

```yaml
# documentation-manifest.yaml — Required outputs per project
required_docs:
  readme:
    file: "README.md"
    sections:
      - "Overview (what this does, in 2-3 sentences)"
      - "Architecture (high-level design with diagram reference)"
      - "Prerequisites"
      - "Quick Start (copy-paste to get running)"
      - "Configuration (all env vars with descriptions)"
      - "API Reference (if applicable)"
      - "Development (how to run tests, lint, etc.)"
      - "Deployment"
      - "Troubleshooting"
    validation: "must be >500 words, <3000 words"
    
  api_docs:
    condition: "project has HTTP endpoints"
    tool: "auto-generated from OpenAPI spec"
    format: "openapi.yaml + Redoc HTML"
    validation: "every endpoint documented with request/response examples"
    
  architecture_doc:
    file: "docs/architecture.md"
    must_include:
      - "C4 Context diagram (Mermaid)"
      - "C4 Container diagram (Mermaid)"
      - "Data flow diagram"
      - "Key design decisions (link to ADRs)"
    
  runbook:
    file: "docs/runbook.md"
    must_include:
      - "Health check endpoints"
      - "Common failure modes"
      - "Log locations and formats"
      - "Restart procedures"
      - "Escalation contacts"
      
  changelog:
    file: "CHANGELOG.md"
    format: "Keep a Changelog (https://keepachangelog.com)"
    auto_generated: true  # from conventional commits
```

## 5B. Agent Documentation Generation Rules

```yaml
# Injected into every agent's system prompt for documentation generation
documentation_rules:
  readme:
    - "Write for a developer who has never seen this project"
    - "Quick Start must be copy-paste-able — test it yourself before generating"
    - "Every environment variable must be documented with: name, description, default value, required/optional"
    - "Include a real curl command example for every API endpoint"
    - "Never write 'TODO' or 'TBD' in documentation"
    
  code_comments:
    - "Document WHY, not WHAT — the code shows what, comments explain why"
    - "Every public function/method gets a docstring with: description, parameters, return type, raises, example"
    - "Complex algorithms get inline comments explaining the approach"
    - "No commented-out code — ever"
    
  api_docs:
    - "Every endpoint: method, path, description, request body schema, response schema, error responses, example"
    - "Use realistic example values, not 'string' or 'example'"
    - "Document rate limits, authentication requirements, pagination"
```

## 5C. Documentation Validation Pipeline

```bash
# doc_validator.sh — Run in pipeline Stage 7b

# Validate README exists and meets minimum standards
if [ ! -f README.md ]; then
    echo "FAIL: README.md missing"
    exit 1
fi

# Check README word count
WORD_COUNT=$(wc -w < README.md)
if [ "$WORD_COUNT" -lt 500 ]; then
    echo "FAIL: README.md too short ($WORD_COUNT words, minimum 500)"
    exit 1
fi

# Check for required sections
for section in "Quick Start" "Configuration" "Development" "Deployment"; do
    if ! grep -qi "$section" README.md; then
        echo "FAIL: README.md missing required section: $section"
        exit 1
    fi
done

# Validate OpenAPI spec if present
if [ -f openapi.yaml ]; then
    npx @redocly/cli lint openapi.yaml --config redocly.yaml
fi

# Check all links in markdown files are valid
find docs/ -name "*.md" -exec markdown-link-check {} \;

# Validate Mermaid diagrams render
find docs/ -name "*.md" -exec grep -l "```mermaid" {} \; | while read file; do
    mmdc -i "$file" -o /tmp/diagram-check.svg 2>&1 || echo "WARN: Invalid Mermaid in $file"
done

# Run doctests (code examples in documentation must execute)
python -m doctest README.md 2>/dev/null || true
pytest --doctest-modules src/ || echo "WARN: Doctest failures detected"
```

---

# DIMENSION 6: COMPLIANCE, ACCESSIBILITY & INTERNATIONALIZATION

**The Problem:** When your system generates applications for clients, those applications may need to comply with regulations (GDPR, SOC 2, HIPAA, PCI DSS), be accessible (WCAG 2.1), and support multiple languages. None of this is currently in your pipeline.

**What Elite Organizations Have:** Compliance is baked into the development process, not bolted on at the end. Apple rejects apps that fail accessibility. Google requires GDPR compliance for all user-facing services.

## 6A. Compliance Rules Engine

```yaml
# compliance-profiles.yaml — Selected per project
profiles:
  gdpr:
    name: "GDPR Compliance"
    applicable_when: "project handles EU personal data"
    rules:
      - id: "GDPR-001"
        rule: "All PII fields must be encrypted at rest"
        check: "grep for PII field patterns, verify encryption wrapper"
        severity: "critical"
      - id: "GDPR-002"
        rule: "Consent must be collected before data processing"
        check: "verify consent_collected check before any data write"
        severity: "critical"
      - id: "GDPR-003"
        rule: "Data deletion endpoint must exist"
        check: "verify DELETE endpoint for user data"
        severity: "critical"
      - id: "GDPR-004"
        rule: "Data export endpoint must exist (right to portability)"
        check: "verify export endpoint returns JSON/CSV"
        severity: "high"
      - id: "GDPR-005"
        rule: "Processing activities must be logged"
        check: "verify audit trail for all data operations"
        severity: "high"
      - id: "GDPR-006"
        rule: "PII must not appear in logs"
        check: "verify log scrubbing for email, phone, SSN, IP patterns"
        severity: "critical"
  
  soc2:
    name: "SOC 2 Type II Compliance"
    applicable_when: "project is a SaaS service"
    rules:
      - id: "SOC2-001"
        rule: "All endpoints require authentication"
        check: "verify auth middleware on all routes except /health"
        severity: "critical"
      - id: "SOC2-002"
        rule: "All actions must be audit-logged"
        check: "verify audit log entries for create/update/delete"
        severity: "critical"
      - id: "SOC2-003"
        rule: "Secrets must not be in source code"
        check: "gitleaks + trufflehog scan"
        severity: "critical"
      - id: "SOC2-004"
        rule: "Access controls must enforce least privilege"
        check: "verify RBAC/ABAC implementation"
        severity: "high"
      - id: "SOC2-005"
        rule: "All data in transit must be encrypted (TLS)"
        check: "verify TLS configuration"
        severity: "critical"
  
  hipaa:
    name: "HIPAA Compliance"
    applicable_when: "project handles protected health information (PHI)"
    rules:
      - id: "HIPAA-001"
        rule: "PHI must be encrypted at rest with AES-256"
        check: "verify field-level encryption for PHI columns"
        severity: "critical"
      - id: "HIPAA-002"
        rule: "Access to PHI must require MFA"
        check: "verify MFA requirement on PHI-accessing endpoints"
        severity: "critical"
      - id: "HIPAA-003"
        rule: "All PHI access must be logged with user identity"
        check: "verify audit trail with user_id for all PHI reads"
        severity: "critical"
      - id: "HIPAA-004"
        rule: "Session timeout must not exceed 15 minutes"
        check: "verify session configuration"
        severity: "high"
  
  pci_dss:
    name: "PCI DSS Compliance"
    applicable_when: "project handles payment card data"
    rules:
      - id: "PCI-001"
        rule: "Card numbers must never be stored in plaintext"
        check: "verify no raw PAN storage, only tokens"
        severity: "critical"
      - id: "PCI-002"
        rule: "CVV must never be stored"
        check: "verify CVV is only held in memory during transaction"
        severity: "critical"
      - id: "PCI-003"
        rule: "All card data in transit must use TLS 1.2+"
        check: "verify TLS configuration"
        severity: "critical"

# Agent prompt injection
compliance_prompt_template: |
  This project requires {profile_name} compliance. You MUST follow these rules:
  {rules_formatted}
  
  Before generating any code that handles regulated data, verify:
  1. Data is encrypted at rest
  2. Access is authenticated and authorized
  3. All operations are audit-logged
  4. PII/PHI/PCI data never appears in logs
  5. Data deletion capability exists
```

## 6B. Accessibility Testing

```yaml
# accessibility-pipeline.yaml — Added to Stage 7c for web projects
accessibility_checks:
  tools:
    - name: "axe-core"
      install: "npm install -g @axe-core/cli"
      command: "axe http://localhost:3000 --exit"
      standard: "WCAG 2.1 AA"
      
    - name: "pa11y"
      install: "npm install -g pa11y"
      command: "pa11y http://localhost:3000 --standard WCAG2AA --reporter json"
      
    - name: "lighthouse"
      install: "npm install -g lighthouse"
      command: "lighthouse http://localhost:3000 --only-categories=accessibility --output=json"
      threshold: 90  # minimum accessibility score
      
  agent_rules:
    - "All images must have alt text that describes the content"
    - "All form inputs must have associated labels"
    - "Color must not be the only means of conveying information"
    - "All interactive elements must be keyboard-accessible"
    - "Focus order must follow logical reading order"
    - "Minimum contrast ratio 4.5:1 for normal text, 3:1 for large text"
    - "All videos must have captions"
    - "Skip navigation link must be the first focusable element"
    - "ARIA roles must be used correctly (prefer semantic HTML)"
    - "Touch targets must be at least 44x44 CSS pixels"
```

## 6C. Internationalization Patterns

```yaml
# i18n-rules.yaml — Injected when project.supports_i18n = true
i18n_rules:
  code_generation:
    - "Never hardcode user-facing strings — extract to translation files"
    - "Use ICU MessageFormat for pluralization and gender"
    - "Store dates as UTC, display in user's timezone"
    - "Use locale-aware number/currency formatting (Intl API or equivalents)"
    - "Support RTL layouts (logical properties: margin-inline-start, not margin-left)"
    - "Never concatenate translated strings — use template variables"
    - "Sort strings using locale-aware collation (Intl.Collator)"
    - "Text expansion: allocate 40% extra space for German/Finnish translations"
    
  file_structure:
    translation_dir: "locales/"
    format: "JSON (flat keys with dot notation)"
    example: |
      // locales/en.json
      {
        "common.save": "Save",
        "common.cancel": "Cancel",
        "invoice.title": "Invoice #{number}",
        "invoice.total": "{amount, number, currency}"
      }
      
      // locales/de.json
      {
        "common.save": "Speichern",
        "common.cancel": "Abbrechen",
        "invoice.title": "Rechnung #{number}",
        "invoice.total": "{amount, number, currency}"
      }
```

---

# DIMENSION 7: DATABASE & DATA ARCHITECTURE INTELLIGENCE

**The Problem:** Your system can generate code, but it doesn't have specialized knowledge about database design. Schema design, normalization, indexing strategies, query optimization, migration patterns — these are domains where bad decisions are incredibly expensive to fix later. Your Phase 4 strategic document covers migration safety (checking migrations don't lock tables), but not the intelligence to design schemas correctly in the first place.

**What Elite Organizations Have:** Dedicated database engineers who review every schema change. Google's Spanner team has strict schema design guidelines. Stripe's database patterns are legendary.

## 7A. Schema Design Knowledge Module

```yaml
# Feed into Qdrant collection: "database_design_patterns"
knowledge_sources:
  elite_schemas:
    - source: "PostgreSQL documentation (partitioning, indexing, JSONB)"
      url: "https://www.postgresql.org/docs/current/"
    - source: "Use The Index, Luke (indexing bible)"
      url: "https://use-the-index-luke.com/"
    - source: "Designing Data-Intensive Applications (Martin Kleppmann)"
      topics: ["replication", "partitioning", "consistency", "batch vs stream"]
    - source: "Stripe's API design patterns"
      topics: ["idempotency keys", "versioned schemas", "soft deletes"]
      
  patterns_to_index:
    - "Soft delete pattern (deleted_at timestamp, not physical delete)"
    - "Audit trail pattern (separate audit table with before/after JSONB)"
    - "Event sourcing pattern (append-only event log)"
    - "CQRS pattern (separate read/write models)"
    - "Multi-tenant patterns (schema-per-tenant vs row-level security)"
    - "Temporal tables (valid_from/valid_to for time-travel queries)"
    - "Polymorphic associations (type + id vs separate tables)"
    - "Adjacency list vs nested set vs materialized path (tree structures)"
    - "UUID vs ULID vs Snowflake ID (primary key strategies)"
    - "Composite index ordering (equality predicates first, range predicates last)"
```

## 7B. Schema Review Agent Rules

```yaml
# Injected into agent system prompt when task involves database design
database_design_rules:
  primary_keys:
    - "Use UUIDv7 or ULID for new tables (time-sortable, no coordination)"
    - "Never use auto-increment integers as external identifiers"
    - "Always add a created_at and updated_at timestamp"
    
  indexing:
    - "Every foreign key column must have an index"
    - "Columns used in WHERE clauses with high selectivity need indexes"
    - "Composite indexes: equality columns first, range columns last, included columns after"
    - "Partial indexes for status-filtered queries (WHERE status = 'active')"
    - "Never index boolean columns alone (low selectivity)"
    - "GIN indexes for JSONB columns that are queried"
    
  naming:
    - "Table names: plural snake_case (users, order_items)"
    - "Column names: singular snake_case (email, created_at)"
    - "Foreign keys: {referenced_table_singular}_id (user_id, not users_id)"
    - "Indexes: idx_{table}_{columns} (idx_users_email)"
    - "Constraints: {type}_{table}_{columns} (uq_users_email, fk_orders_user_id)"
    
  migrations:
    - "Every migration must be reversible (include down migration)"
    - "Never rename columns in production — add new, migrate data, drop old"
    - "Add new NOT NULL columns with a DEFAULT value first, then remove default"
    - "Large table migrations must use CREATE INDEX CONCURRENTLY"
    - "Always wrap DDL in transactions (PostgreSQL supports this)"
    - "Test migration on production-size dataset before deploying"
    
  performance:
    - "Avoid SELECT * — always specify columns"
    - "Use EXPLAIN ANALYZE on all generated queries"
    - "N+1 query detection: never query inside a loop"
    - "Use COPY for bulk inserts, not individual INSERTs"
    - "Connection pooling is mandatory (PgBouncer or built-in pool)"
    - "Set statement_timeout to prevent runaway queries"
```

---

# DIMENSION 8: RESOURCE ECONOMICS & MULTI-PROJECT ORCHESTRATION

**The Problem:** LLM tokens cost money. GPU compute costs money. Your system will run multiple projects simultaneously. Without resource management, one complex project could consume all available tokens/compute, starving other projects. You need a scheduler, budgets, and cost attribution.

**What Elite Organizations Have:** Cloud cost management, resource quotas per team, chargeback systems, spot instance management.

## 8A. Token Budget Management

```yaml
# token-budgets.yaml
budgets:
  tiers:
    low:
      max_tokens_per_project: 50_000
      max_concurrent_agents: 1
      model_tier: "small"  # Route to Qwen3-Coder 30B or similar
      use_case: "Simple scripts, small utilities"
      
    medium:
      max_tokens_per_project: 200_000
      max_concurrent_agents: 2
      model_tier: "medium"  # Route to DeepSeek-V3.2 or GLM-4.6
      use_case: "Standard microservices, APIs"
      
    high:
      max_tokens_per_project: 1_000_000
      max_concurrent_agents: 4
      model_tier: "large"  # Route to Devstral 2 123B or Qwen3-Coder 235B
      use_case: "Complex multi-service systems"
      
    unlimited:
      max_tokens_per_project: null
      max_concurrent_agents: 6
      model_tier: "large"
      use_case: "Critical projects, no budget constraint"
      approval_required: true
      
  tracking:
    granularity: "per-agent-per-stage"  # Track tokens at agent + pipeline stage level
    alerts:
      - at: 50%
        action: "log"
      - at: 75%
        action: "notify_mattermost"
      - at: 90%
        action: "notify_mattermost + notify_omi_haptic"
      - at: 100%
        action: "pause_project + require_approval_to_continue"
```

## 8B. GPU Scheduling & Cost Optimization

```python
# gpu_scheduler.py — Manages on-demand GPU instances

class GPUScheduler:
    """Schedule GPU instances based on project demand."""
    
    def __init__(self, provider: str = "lambda_labs"):
        self.provider = get_provider(provider)  # Lambda, CoreWeave, etc.
        self.active_instances = {}
        self.queue = PriorityQueue()
    
    def schedule_work(self, project: Project, estimated_tokens: int):
        """Decide whether to use existing instance, spin up new, or queue."""
        
        required_vram = estimate_vram_requirement(project.model_tier)
        
        # Check if we have a running instance with capacity
        for instance_id, instance in self.active_instances.items():
            if instance.available_vram >= required_vram:
                return self.assign_to_instance(project, instance_id)
        
        # Check if spinning up a new instance is cost-effective
        estimated_duration = estimate_duration(estimated_tokens, project.model_tier)
        instance_cost = self.provider.estimate_cost(required_vram, estimated_duration)
        
        if instance_cost < project.budget_remaining:
            instance_id = self.provider.create_instance(
                gpu_type=select_gpu(required_vram),
                preemptible=project.priority != "critical"  # Use spot for non-critical
            )
            self.active_instances[instance_id] = instance_id
            return self.assign_to_instance(project, instance_id)
        
        # Queue for when an instance becomes available
        self.queue.put((project.priority, project))
        notify_mattermost(f"Project {project.name} queued — waiting for GPU capacity")
    
    def auto_shutdown_idle(self):
        """Shut down instances that have been idle for >10 minutes."""
        for instance_id, instance in list(self.active_instances.items()):
            if instance.idle_seconds > 600:
                self.provider.terminate_instance(instance_id)
                del self.active_instances[instance_id]
                
                # Process queue
                while not self.queue.empty():
                    priority, project = self.queue.get()
                    self.schedule_work(project, project.estimated_tokens)
```

## 8C. Cost Attribution & Reporting

```python
# cost_reporter.py
def generate_weekly_cost_report():
    """Generate per-project cost breakdown."""
    
    projects = get_all_projects(period="last_7_days")
    
    report = {
        "period": "2026-W05",
        "total_cost_usd": 0,
        "projects": []
    }
    
    for project in projects:
        project_cost = {
            "name": project.name,
            "token_consumption": project.total_tokens,
            "token_cost_usd": project.total_tokens * TOKEN_COST_PER_1K / 1000,
            "gpu_hours": project.gpu_hours,
            "gpu_cost_usd": project.gpu_hours * GPU_COST_PER_HOUR,
            "storage_gb": project.storage_gb,
            "storage_cost_usd": project.storage_gb * STORAGE_COST_PER_GB,
            "breakdown_by_stage": {
                stage: {
                    "tokens": usage.tokens,
                    "duration_minutes": usage.duration_minutes,
                    "cost_usd": usage.estimated_cost
                }
                for stage, usage in project.stage_usage.items()
            }
        }
        project_cost["total_cost_usd"] = (
            project_cost["token_cost_usd"] + 
            project_cost["gpu_cost_usd"] + 
            project_cost["storage_cost_usd"]
        )
        report["total_cost_usd"] += project_cost["total_cost_usd"]
        report["projects"].append(project_cost)
    
    # Store report and send to Mattermost
    store_report(report)
    send_cost_summary_to_mattermost(report)
    
    return report
```

---

# DIMENSION 9: CODEBASE UNDERSTANDING & MIGRATION INTELLIGENCE

**The Problem:** Your system excels at generating new code from specifications. But a huge portion of real engineering work involves understanding and modifying existing code — legacy codebases, framework migrations, dependency upgrades, dead code elimination. Your agents need the ability to comprehend existing code, not just write new code.

**What Elite Organizations Have:** Facebook's LLM-powered code understanding tools. Google's Code Comprehension infrastructure. Apple's automated migration tools for Swift version upgrades.

## 9A. Codebase Analysis Agent

```yaml
# codebase-analysis-rules.yaml — For when agents receive existing code
analysis_capabilities:
  code_archaeology:
    purpose: "Understand what existing code does and why"
    steps:
      - "Map the dependency graph (who imports what)"
      - "Identify entry points (main, CLI, API routes, event handlers)"
      - "Trace data flow from input to output"
      - "Identify design patterns in use"
      - "Flag dead code (unreachable functions, unused imports)"
      - "Identify tech debt hotspots (complexity, coupling, test gaps)"
    output: "docs/codebase-analysis.md with architecture diagram"
    
  framework_migration:
    purpose: "Migrate between frameworks or language versions"
    examples:
      - "Flask → FastAPI"
      - "Express → Fastify"
      - "React Class Components → Hooks"
      - "SQLAlchemy 1.x → 2.0"
      - "Python 3.8 → 3.12"
      - "Django REST Framework → Ninja"
    approach:
      - "Analyze current framework usage patterns"
      - "Map current APIs to target framework equivalents"
      - "Generate migration plan with ordered steps"
      - "Migrate file-by-file, running tests after each"
      - "Update all imports, configuration, deployment files"
      - "Verify full test suite passes on new framework"
      
  dependency_upgrade:
    purpose: "Safely upgrade dependencies"
    steps:
      - "Identify all direct and transitive dependencies"
      - "Check each for known vulnerabilities (OSV, NVD)"
      - "Identify breaking changes in changelogs"
      - "Generate upgrade plan (order matters — upgrade deps of deps first)"
      - "Upgrade one at a time, running tests after each"
      - "If tests fail, analyze the failure and adapt code"
      
  dead_code_elimination:
    purpose: "Remove code that is never executed"
    tools:
      - "vulture (Python): finds unused code"
      - "ts-prune (TypeScript): finds unused exports"
      - "cargo-udeps (Rust): finds unused dependencies"
    approach:
      - "Run dead code detection tool"
      - "Cross-reference with test coverage data"
      - "Cross-reference with production usage data (if available)"
      - "Generate removal PR with explanation for each deletion"
      - "Never remove code that's only referenced dynamically (reflection, string-based imports)"
```

## 9B. Legacy Code Comprehension Prompt

```yaml
# Injected when agent is given an existing codebase to understand
legacy_comprehension_prompt: |
  You are analyzing an existing codebase. Before making ANY changes:
  
  1. READ the entire project structure. List every file and its purpose.
  2. MAP the dependency graph. What imports what?
  3. IDENTIFY entry points. How does this code get executed?
  4. TRACE one complete request path from input to output.
  5. IDENTIFY patterns: what architectural patterns are in use?
  6. IDENTIFY problems: what would you change if writing from scratch?
  7. CHECK tests: what's tested, what's not?
  8. CHECK documentation: is it accurate? Is it missing?
  
  Only after completing this analysis should you proceed with modifications.
  
  When modifying legacy code:
  - Preserve existing behavior unless explicitly asked to change it
  - Add tests for any code you touch that isn't already tested
  - Document WHY you changed things in commit messages
  - If you find a bug, fix it separately from feature work (separate commit)
  - Never rewrite working code just because you'd write it differently
```

---

# DIMENSION 10: BUILD SYSTEM INTELLIGENCE

**The Problem:** Your Phase 3 covers build caching (ccache, sccache, Turborepo) but not the deeper build system intelligence that elite organizations rely on. Google's entire engineering culture is built around Bazel. Facebook's Buck2 enables massive-scale monorepo development. These aren't just "faster builds" — they're fundamentally different engineering paradigms.

**What Elite Organizations Have:** Hermetic builds, test impact analysis (only run tests affected by changes), remote build execution, build dependency graphs.

## 10A. Test Impact Analysis

Only run tests affected by code changes — critical for large projects:

```python
# test_impact_analyzer.py
import ast
from pathlib import Path

class TestImpactAnalyzer:
    """Determine which tests to run based on changed files."""
    
    def __init__(self, project_path: str):
        self.project = Path(project_path)
        self.dependency_graph = self.build_import_graph()
    
    def build_import_graph(self) -> dict[str, set[str]]:
        """Map every file to the files it imports."""
        graph = {}
        for py_file in self.project.rglob("*.py"):
            module = self.file_to_module(py_file)
            imports = self.extract_imports(py_file)
            graph[module] = imports
        return graph
    
    def get_affected_tests(self, changed_files: list[str]) -> list[str]:
        """Given changed files, return which test files need to run."""
        changed_modules = {self.file_to_module(Path(f)) for f in changed_files}
        
        # Find all modules that transitively depend on changed modules
        affected = set()
        for module in changed_modules:
            affected |= self.get_reverse_dependencies(module)
        
        # Filter to only test files
        test_files = [
            self.module_to_file(m) for m in affected
            if m.startswith("tests.") or m.startswith("test_")
        ]
        
        return test_files
    
    def get_reverse_dependencies(self, module: str) -> set[str]:
        """Find all modules that (transitively) import the given module."""
        reverse_deps = set()
        queue = [module]
        
        while queue:
            current = queue.pop()
            for mod, imports in self.dependency_graph.items():
                if current in imports and mod not in reverse_deps:
                    reverse_deps.add(mod)
                    queue.append(mod)
        
        return reverse_deps

# Usage in pipeline:
# changed_files = git_diff("HEAD~1", "HEAD")
# analyzer = TestImpactAnalyzer(".")
# affected_tests = analyzer.get_affected_tests(changed_files)
# pytest.main(affected_tests)  # Only run affected tests
```

## 10B. Monorepo Intelligence

```yaml
# monorepo-config.yaml — For projects with multiple packages
monorepo:
  tool: "turborepo"  # or nx, lerna, pnpm workspaces
  
  workspace_detection:
    - "If project has multiple packages/ or services/ directories → monorepo"
    - "If project has a root package.json with workspaces → monorepo"
    - "If project has a pnpm-workspace.yaml → monorepo"
    
  agent_rules:
    - "Never install dependencies at the root — install in the specific package"
    - "Shared types/utilities go in a packages/shared/ package"
    - "Each service has its own Dockerfile"
    - "Use workspace-level scripts for cross-cutting operations"
    - "CI must build/test only affected packages (use --filter=...[HEAD~1])"
    
  build_optimization:
    - "Enable Turborepo remote caching for CI"
    - "Use incremental TypeScript compilation (tsconfig with references)"
    - "Docker layer caching for monorepo builds (copy package.json first, then source)"
```

---

# DIMENSION 11: KNOWLEDGE GOVERNANCE & CURATION

**The Problem:** Your knowledge base will grow continuously — algorithm examples, design patterns, anti-patterns, platform modules, academic papers, codebases, feedback data. Without governance, the knowledge base becomes a swamp: duplicates, outdated content, contradictory advice, low-quality entries diluting high-quality ones.

**What Elite Organizations Have:** Google's knowledge management systems have quality scores, freshness signals, and automated deprecation. Wikipedia has editorial policies and deletion criteria.

## 11A. Knowledge Quality Framework

```python
# knowledge_governor.py

class KnowledgeGovernor:
    """Manages knowledge quality across all Qdrant collections."""
    
    COLLECTIONS = [
        "algorithms", "design_patterns", "anti_patterns", 
        "platform_modules", "academic_papers", "codebase_examples",
        "human_feedback", "incident_reports"
    ]
    
    def quality_audit(self, collection: str):
        """Score every knowledge entry for continued relevance."""
        
        entries = qdrant_client.scroll(collection, limit=1000)
        
        for entry in entries:
            score = self.calculate_quality_score(entry)
            
            if score < 0.3:
                # Mark for deletion review
                self.flag_for_review(entry, reason="low_quality_score")
                
            elif score < 0.5:
                # Mark as potentially outdated
                self.flag_for_review(entry, reason="potentially_outdated")
    
    def calculate_quality_score(self, entry) -> float:
        """Score based on multiple signals."""
        
        scores = []
        
        # Freshness: when was this added/updated?
        age_days = (datetime.utcnow() - entry.metadata["created_at"]).days
        freshness = max(0, 1 - (age_days / 730))  # Decay over 2 years
        scores.append(("freshness", freshness, 0.2))
        
        # Usage: how often has this been retrieved by agents?
        retrieval_count = entry.metadata.get("retrieval_count", 0)
        usage = min(1, retrieval_count / 50)  # Normalized to 50 retrievals
        scores.append(("usage", usage, 0.3))
        
        # Effectiveness: when retrieved, did it improve output quality?
        effectiveness = entry.metadata.get("effectiveness_score", 0.5)
        scores.append(("effectiveness", effectiveness, 0.3))
        
        # Source quality: is the source authoritative?
        source_tier = entry.metadata.get("source_tier", "unknown")
        source_scores = {"elite": 1.0, "good": 0.7, "community": 0.5, "unknown": 0.3}
        scores.append(("source", source_scores.get(source_tier, 0.3), 0.2))
        
        return sum(score * weight for _, score, weight in scores)
    
    def deduplication(self, collection: str):
        """Find and merge near-duplicate entries."""
        
        entries = qdrant_client.scroll(collection, limit=1000)
        
        for i, entry_a in enumerate(entries):
            for entry_b in entries[i+1:]:
                similarity = cosine_similarity(entry_a.vector, entry_b.vector)
                
                if similarity > 0.95:  # Near-duplicate
                    # Keep the one with higher quality score
                    keep, remove = sorted(
                        [entry_a, entry_b],
                        key=lambda e: self.calculate_quality_score(e),
                        reverse=True
                    )
                    
                    # Merge metadata (combine retrieval counts, etc.)
                    merge_metadata(keep, remove)
                    qdrant_client.delete(collection, ids=[remove.id])
    
    def knowledge_retirement(self, collection: str):
        """Retire knowledge that is demonstrably outdated or harmful."""
        
        entries = qdrant_client.scroll(collection, limit=1000)
        
        for entry in entries:
            # Check if the knowledge has been contradicted by newer entries
            newer_entries = self.find_contradictions(entry, collection)
            if newer_entries:
                self.retire_entry(entry, reason="contradicted_by_newer_knowledge")
                continue
            
            # Check if the source has been deprecated
            if entry.metadata.get("source_url"):
                if is_url_dead(entry.metadata["source_url"]):
                    self.flag_for_review(entry, reason="source_url_dead")
    
    def provenance_tracking(self, entry_id: str) -> dict:
        """Track the full lineage of a knowledge entry."""
        
        entry = qdrant_client.get(entry_id)
        
        return {
            "entry_id": entry_id,
            "original_source": entry.metadata["source"],
            "source_url": entry.metadata.get("source_url"),
            "ingestion_date": entry.metadata["created_at"],
            "last_updated": entry.metadata.get("updated_at"),
            "retrieval_history": entry.metadata.get("retrieval_log", []),
            "effectiveness_history": entry.metadata.get("effectiveness_log", []),
            "quality_score": self.calculate_quality_score(entry),
            "related_entries": self.find_related(entry_id)
        }
```

## 11B. Knowledge Ingestion Quality Gate

```yaml
# knowledge-ingestion-rules.yaml
ingestion_rules:
  before_adding:
    - "Check for duplicates (cosine similarity > 0.9 with existing entries)"
    - "Verify source license is compatible (Apache-2.0, MIT, BSD, public domain)"
    - "Verify source is actively maintained (last commit < 2 years ago)"
    - "Verify content is not trivial (must teach something non-obvious)"
    - "Assign source tier: elite (top 100 repos), good (1K+ stars), community (other)"
    
  metadata_required:
    - "source: where did this come from?"
    - "source_url: link to original"
    - "source_license: SPDX identifier"
    - "source_tier: elite | good | community"
    - "language: programming language"
    - "domain: algorithm | pattern | anti-pattern | platform | etc."
    - "ingestion_date: when was this added"
    - "retrieval_count: 0 (initialized)"
    - "effectiveness_score: null (not yet measured)"
    
  scheduled_maintenance:
    deduplication: "weekly"
    quality_audit: "monthly"
    retirement_check: "monthly"
    freshness_update: "weekly"
```

---

# DIMENSION 12: DISASTER RECOVERY & SYSTEM BACKUP

**The Problem:** You're building a complex system with 50+ Docker services, terabytes of knowledge in Qdrant and Neo4j, project configurations, agent prompts, pipeline rules, and historical data. If a disk fails, a cloud instance gets terminated, or a misconfiguration corrupts data, can you recover?

**What Elite Organizations Have:** Automated backups with tested recovery procedures, RTO/RPO targets, regular disaster recovery drills.

## 12A. Backup Strategy

```yaml
# backup-strategy.yaml
backup:
  critical_data:
    qdrant_vectors:
      method: "qdrant snapshot API"
      frequency: "daily"
      retention: "30 days"
      destination: "encrypted S3-compatible (MinIO or Backblaze B2)"
      command: |
        curl -X POST "http://omni-qdrant:6333/collections/{name}/snapshots"
        # Download and encrypt
        gpg --symmetric --cipher-algo AES256 snapshot.tar
        
    neo4j_graph:
      method: "neo4j-admin dump"
      frequency: "daily"
      retention: "30 days"
      command: |
        docker exec omni-neo4j neo4j-admin database dump neo4j --to-path=/backups/
        
    postgresql:
      method: "pg_dump"
      frequency: "daily" 
      retention: "30 days"
      command: |
        docker exec omni-postgres pg_dump -U omni -Fc control_plane > backup.dump
        
    redis:
      method: "redis-cli BGSAVE + copy RDB"
      frequency: "hourly"
      retention: "7 days"
      
  important_data:
    project_configs:
      method: "git repository (all configs in version control)"
      frequency: "on every change (git push)"
      retention: "permanent"
      
    agent_prompts:
      method: "versioned in git with semantic versioning"
      frequency: "on every change"
      retention: "permanent"
      
    pipeline_rules:
      method: "versioned in git"
      frequency: "on every change"
      retention: "permanent"
      
    golden_test_baselines:
      method: "git LFS for large test fixtures"
      frequency: "on every update"
      retention: "permanent"
      
  system_config:
    docker_compose_files:
      method: "git repository"
    environment_variables:
      method: "encrypted in Infisical, backed up with Infisical's backup"
    ssl_certificates:
      method: "backed up to encrypted storage"
      frequency: "on renewal"

  recovery:
    rto: "4 hours"  # Recovery Time Objective
    rpo: "24 hours"  # Recovery Point Objective (max data loss)
    
    procedure:
      - "1. Provision new infrastructure (cloud instance or local machine)"
      - "2. Clone configuration repository"
      - "3. Restore environment variables from Infisical backup"
      - "4. docker-compose up -d (core infrastructure: postgres, redis, qdrant, neo4j)"
      - "5. Restore PostgreSQL from latest backup"
      - "6. Restore Qdrant from latest snapshot"
      - "7. Restore Neo4j from latest dump"
      - "8. docker-compose up -d (all services)"
      - "9. Run health checks on all services"
      - "10. Run golden test suite to verify system functionality"
      
    drill_schedule: "quarterly"  # Test recovery procedure every 3 months
```

## 12B. Backup Automation

```yaml
# docker-compose.backup.yml
services:
  omni-backup:
    image: python:3.12-slim
    container_name: omni-backup
    labels:
      - "omni.system=backup"
      - "omni.tier=infrastructure"
    volumes:
      - ./backup-scripts:/app
      - ./backups:/backups
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - BACKUP_ENCRYPTION_KEY=${BACKUP_ENCRYPTION_KEY}
      - S3_ENDPOINT=${S3_ENDPOINT}
      - S3_BUCKET=${S3_BUCKET}
      - S3_ACCESS_KEY=${S3_ACCESS_KEY}
      - S3_SECRET_KEY=${S3_SECRET_KEY}
      - MATTERMOST_WEBHOOK_URL=${MATTERMOST_WEBHOOK_URL}
    networks:
      - omni-quantum-network
    # Run daily at 2 AM
    entrypoint: ["crond", "-f"]
    restart: unless-stopped
```

---

# UPDATED INFRASTRUCTURE SUMMARY

## New Docker Services (This Document: 4)

| Service | Container Name | Port | Purpose |
|---------|---------------|------|---------|
| Control Plane | omni-control-plane | 8300 | Dashboard, project management, approvals |
| Code Index | omni-code-index | 8310 | Codebase semantic indexing |
| Backup Automation | omni-backup | — | Automated backups |
| Auth (Optional) | omni-authentik | 8320 | SSO/RBAC for dashboard |

## New Sandbox/Pipeline Tools (No separate containers)

| Tool | Purpose | Pipeline Stage |
|------|---------|---------------|
| axe-core | Accessibility testing | 7c |
| pa11y | Accessibility testing | 7c |
| lighthouse | Accessibility + performance audit | 7c |
| markdown-link-check | Documentation link validation | 7b |
| mmdc (Mermaid CLI) | Diagram validation | 7b |
| trivy | Container image scanning | 9 |
| cosign | Container image signing | 9 |
| syft | SBOM generation | 9 |
| vulture | Python dead code detection | Analysis |
| ts-prune | TypeScript dead code detection | Analysis |
| cargo-udeps | Rust unused dependency detection | Analysis |

## Cumulative Architecture (All Phases Combined)

| Metric | Count |
|--------|-------|
| Always-On Docker Services | **54** |
| With On-Demand Services | **62** |
| Total Integrated Tools | **125+** |
| Pipeline Stages | **11** (original 8 + build + staging + production) |
| Pipeline Sub-Stages | **40+** |
| Knowledge Domains | **14** |
| Agent Roles | **5** (Architect, Developer, Tester, Reviewer, Optimizer) |
| Golden Test Cases | **20+** (covering diverse project types) |
| Compliance Profiles | **4** (GDPR, SOC 2, HIPAA, PCI DSS) |
| Backup Targets | **6** (Qdrant, Neo4j, PostgreSQL, Redis, configs, prompts) |

---

# IMPLEMENTATION PRIORITY

## Phase 0: Immediate (Do This First)
1. **Control Plane Dashboard** (Dimension 1) — Without this, everything else is hard to manage
2. **Context Engineering** (Dimension 3) — Highest-leverage improvement for code quality
3. **Golden Test Suites** (Dimension 2A) — Need baselines before making more changes

## Phase 1: Week 1-2
4. **Documentation Generation Rules** (Dimension 5) — Inject into agent prompts immediately
5. **Database Design Rules** (Dimension 7B) — Inject into agent prompts immediately
6. **Backup Automation** (Dimension 12) — Protect what you've built

## Phase 2: Week 2-3
7. **Delivery Pipeline** (Dimension 4) — Extend pipeline from code-gen to deployment
8. **Token Budget Management** (Dimension 8A) — Essential for cost control
9. **Codebase Analysis Agent** (Dimension 9) — Enable working with existing code

## Phase 3: Week 3-4
10. **Agent Benchmarking** (Dimension 2B) — SWE-bench, HumanEval integration
11. **Compliance Profiles** (Dimension 6A) — Enable when projects require it
12. **Knowledge Governance** (Dimension 11) — Before the knowledge base grows too large

## Phase 4: Ongoing
13. **Accessibility Testing** (Dimension 6B) — For web-facing projects
14. **Build System Intelligence** (Dimension 10) — As monorepo projects emerge
15. **A/B Testing Configurations** (Dimension 2C) — Continuous optimization
16. **GPU Scheduling** (Dimension 8B) — As multi-project demand grows

---

# THE COMPLETE PICTURE

After all four phases plus these 12 dimensions, here is what the Omni Quantum Elite AI Coding System covers:

**INPUT → UNDERSTANDING → GENERATION → VALIDATION → DEPLOYMENT → MONITORING → LEARNING**

| Stage | What Happens |
|-------|-------------|
| **Request** | Structured project request via Control Plane dashboard |
| **Specification** | Agent generates spec.md with mandatory sections → Human approval gate |
| **Context Assembly** | Intelligent context selection from codebase index, knowledge base, ADRs, feedback |
| **Design Review** | Multi-dimensional design review with score-based proceed/revise/escalate |
| **Code Generation** | Multi-agent collaboration (Architect → Developer → Tester → Reviewer → Optimizer) |
| **Quality Pipeline** | 40+ sub-stages: linting, type checking, security scanning, coverage, fuzzing, mutation testing, formal verification, symbolic execution, complexity analysis, architecture enforcement, policy checks, accessibility, compliance, documentation validation |
| **Documentation** | Auto-generated README, API docs, architecture diagrams, runbooks, changelogs |
| **Build** | Container build, scan, SBOM, signing |
| **Staging** | Auto-deploy to staging, smoke tests, integration tests, load tests |
| **Production** | Human approval → blue-green/canary deployment → health monitoring → auto-rollback |
| **Monitoring** | SLOs, error tracking, distributed tracing, cost attribution |
| **Learning** | Post-incident analysis → anti-pattern updates → agent self-evaluation → knowledge refresh → prompt optimization |

**This is no longer a tool collection. This is an autonomous software engineering organization.**

---

# WHAT'S LEFT AFTER THIS?

After implementing these 12 dimensions on top of the previous 4 phases, the only remaining gaps would be:

1. **Domain-Specific Intelligence** — Specialized knowledge for specific industries (fintech, healthtech, edtech). This is project-specific and added as needed.

2. **Multi-Agent Negotiation** — Agents that can disagree, debate, and converge on solutions. This is cutting-edge research (AutoGen, CrewAI) and not yet production-ready.

3. **Self-Modifying Pipeline** — The system detecting that its own pipeline has a gap and adding a new stage automatically. This is AGI-territory and not something to engineer today.

4. **Natural Language DevOps** — "Deploy the invoice service to production" via voice command through Omi. This is an integration project, not a capability gap.

Everything else — the fundamentals of how elite software is engineered, validated, deployed, monitored, and improved — is covered.
