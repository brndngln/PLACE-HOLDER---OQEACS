# Master Orchestrator API Reference

## Overview

The Master Orchestrator coordinates all 37 systems in the Omni Quantum Elite platform. It manages the 8-stage AI coding pipeline, handles inter-service communication, orchestrates complex workflows, and provides a unified control plane for platform operations.

**Container**: `omni-orchestrator` | **Port**: 8080 | **Tier**: Core

### Authentication
All endpoints require a Bearer token: `Authorization: Bearer ${ORCHESTRATOR_TOKEN}`

---

## Pipeline Orchestration

### Execute Pipeline

**POST** `/api/v1/pipeline/execute`

Execute the full 8-stage AI coding pipeline or a subset of stages.

```json
{
  "task": "Implement user authentication with JWT tokens",
  "stages": ["ingest", "enrich", "generate", "validate", "test"],
  "config": {
    "model": "gpt-4o",
    "language": "python",
    "repo_url": "http://omni-gitea:3000/omni-admin/my-project.git",
    "branch": "feature/auth",
    "max_iterations": 3,
    "quality_gate": "strict"
  },
  "context": {
    "knowledge_sources": ["neo4j", "qdrant", "wiki"],
    "max_context_tokens": 16000
  }
}
```

**Response**:
```json
{
  "pipeline_id": "pipe_abc123",
  "status": "running",
  "stages": {
    "ingest": {"status": "completed", "duration_ms": 2340},
    "enrich": {"status": "running", "started_at": "2025-01-15T10:30:05Z"},
    "generate": {"status": "pending"},
    "validate": {"status": "pending"},
    "test": {"status": "pending"}
  },
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Get Pipeline Status

**GET** `/api/v1/pipeline/{pipeline_id}`

Returns current status of all stages including logs and artifacts.

### List Pipelines

**GET** `/api/v1/pipeline`

Query parameters:
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter: `running`, `completed`, `failed`, `cancelled` |
| `since` | string | ISO timestamp |
| `limit` | int | Max results (default: 20) |

### Cancel Pipeline

**POST** `/api/v1/pipeline/{pipeline_id}/cancel`

Gracefully cancels a running pipeline. In-progress stages complete; pending stages are skipped.

---

## Service Management

### List Services

**GET** `/api/v1/services`

Returns health and status of all 37 managed services.

```json
{
  "services": [
    {
      "name": "neo4j-graphrag-api",
      "container": "omni-neo4j-graphrag-api",
      "port": 7475,
      "tier": "Knowledge",
      "status": "healthy",
      "uptime_seconds": 86400,
      "last_health_check": "2025-01-15T10:29:55Z",
      "version": "2.0.0"
    }
  ],
  "summary": {
    "total": 37,
    "healthy": 35,
    "degraded": 1,
    "unhealthy": 1
  }
}
```

### Get Service Detail

**GET** `/api/v1/services/{name}`

Returns detailed service information including configuration, dependencies, and recent metrics.

### Restart Service

**POST** `/api/v1/services/{name}/restart`

Restarts a specific service container. Waits for health check to pass before returning.

### Service Dependencies

**GET** `/api/v1/services/{name}/dependencies`

Returns the dependency graph for a service (what it depends on and what depends on it).

---

## Knowledge Operations

### Trigger Knowledge Refresh

**POST** `/api/v1/knowledge/refresh`

Forces a full knowledge layer refresh: checks freshness, re-ingests stale sources, rebuilds caches.

```json
{
  "sources": ["all"],
  "force_reingest": false,
  "rebuild_cache": true,
  "collections": ["code_embeddings", "doc_embeddings"]
}
```

### Knowledge Status

**GET** `/api/v1/knowledge/status`

Returns status of all knowledge layer components:
```json
{
  "qdrant": {
    "status": "healthy",
    "collections": 4,
    "total_points": 125000
  },
  "neo4j": {
    "status": "healthy",
    "patterns": 54,
    "relationships": 120
  },
  "wiki": {
    "status": "healthy",
    "pages": 16,
    "last_sync": "2025-01-15T10:00:00Z"
  },
  "semantic_cache": {
    "status": "healthy",
    "entries": 5420,
    "hit_rate": 0.73
  },
  "freshness": {
    "sources_monitored": 12,
    "stale_sources": 1,
    "last_check": "2025-01-15T10:15:00Z"
  }
}
```

---

## Workflow Management

### Create Workflow

**POST** `/api/v1/workflows`

Create a custom multi-step workflow that chains service operations.

```json
{
  "name": "code-review-pipeline",
  "description": "Automated code review with AI analysis",
  "trigger": {
    "type": "webhook",
    "event": "push",
    "filter": {"branch": "main"}
  },
  "steps": [
    {
      "name": "analyze",
      "service": "neo4j-graphrag-api",
      "action": "POST /patterns/recommend",
      "input": {"task": "{{event.commit_message}}"}
    },
    {
      "name": "scan",
      "service": "security-shield",
      "action": "POST /api/v1/scan",
      "input": {"repo": "{{event.repo_url}}", "commit": "{{event.sha}}"},
      "depends_on": []
    },
    {
      "name": "review",
      "service": "ai-coder-alpha",
      "action": "POST /api/v1/tasks",
      "input": {
        "instruction": "Review the latest commit: {{event.sha}}",
        "context": "{{steps.analyze.output}}"
      },
      "depends_on": ["analyze", "scan"]
    }
  ]
}
```

### List Workflows

**GET** `/api/v1/workflows`

### Execute Workflow

**POST** `/api/v1/workflows/{id}/execute`

### Workflow Execution History

**GET** `/api/v1/workflows/{id}/executions`

---

## Configuration

### Get Platform Config

**GET** `/api/v1/config`

Returns the current platform configuration (redacted secrets).

### Update Service Config

**PATCH** `/api/v1/config/services/{name}`

Update a service's configuration. Changes are applied on next restart.

```json
{
  "environment": {
    "LITELLM_MODEL": "gpt-4o",
    "MAX_TOKENS": "8000"
  },
  "resources": {
    "memory_limit": "4g",
    "cpu_limit": "2.0"
  }
}
```

---

## Events and Webhooks

### List Recent Events

**GET** `/api/v1/events`

Query parameters: `type`, `service`, `since`, `limit`

### Register Webhook

**POST** `/api/v1/webhooks`

```json
{
  "url": "http://omni-n8n:5678/webhook/pipeline-complete",
  "events": ["pipeline.completed", "pipeline.failed"],
  "secret": "webhook_signing_secret"
}
```

### Event Types

| Event | Description |
|-------|-------------|
| `pipeline.started` | Pipeline execution began |
| `pipeline.stage.completed` | A pipeline stage finished |
| `pipeline.completed` | Full pipeline completed successfully |
| `pipeline.failed` | Pipeline failed at a stage |
| `service.health_changed` | Service health status changed |
| `service.restarted` | Service was restarted |
| `knowledge.refreshed` | Knowledge layer refresh completed |
| `knowledge.source.stale` | A knowledge source became stale |
| `workflow.completed` | Custom workflow finished |
| `workflow.failed` | Custom workflow failed |

---

## Observability

### Platform Metrics

**GET** `/api/v1/metrics/summary`

Aggregated metrics across all services:
```json
{
  "period": "last_24h",
  "requests_total": 45230,
  "errors_total": 123,
  "error_rate": 0.0027,
  "avg_latency_ms": 145,
  "p99_latency_ms": 890,
  "llm_tokens_used": 2450000,
  "llm_cost_usd": 12.30,
  "pipelines_executed": 34,
  "pipelines_success_rate": 0.94,
  "knowledge_queries": 1200,
  "cache_hit_rate": 0.73
}
```

### Service Metrics

**GET** `/api/v1/metrics/services/{name}`

### Health Dashboard

**GET** `/api/v1/health/dashboard`

Returns a structured health overview suitable for rendering a status page.

---

## Health and Readiness

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Orchestrator liveness |
| GET | `/ready` | Orchestrator readiness (checks all critical services) |
| GET | `/metrics` | Prometheus metrics endpoint |

### Health Response
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 172800,
  "services_healthy": 35,
  "services_total": 37
}
```

---

## Rate Limits

| Endpoint Category | Limit |
|-------------------|-------|
| Pipeline execution | 10/min |
| Service restart | 5/min |
| Knowledge refresh | 2/min |
| Read operations | 100/min |
| Webhook registration | 20/hour |

Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `PIPELINE_RUNNING` | 409 | Pipeline already running for this repo/branch |
| `SERVICE_UNAVAILABLE` | 503 | Target service is unhealthy |
| `STAGE_FAILED` | 500 | Pipeline stage execution failed |
| `RATE_LIMITED` | 429 | Too many requests |
| `INVALID_WORKFLOW` | 400 | Workflow definition is invalid |
| `DEPENDENCY_CYCLE` | 400 | Workflow has circular dependencies |
| `TIMEOUT` | 504 | Operation timed out |

---

*Last updated: 2025-01-01 | The orchestrator is the central control plane — all cross-service operations should go through it.*
