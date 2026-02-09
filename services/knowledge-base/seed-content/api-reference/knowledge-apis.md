# Knowledge Layer APIs Reference

## Knowledge Ingestor — System 18

**Container**: `omni-knowledge-ingestor` | **Port**: 8400 | **Tier**: Knowledge

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/ingest` | Ingest a document or URL |
| POST | `/v1/ingest/batch` | Batch ingest multiple documents |
| GET | `/v1/sources` | List tracked sources |
| GET | `/v1/sources/{id}` | Get source details and status |
| DELETE | `/v1/sources/{id}` | Remove a tracked source |
| POST | `/v1/sources/{id}/reingest` | Force re-ingestion of a source |
| GET | `/v1/stats` | Ingestion statistics |
| GET | `/health` | Health check |
| GET | `/ready` | Readiness (checks Qdrant, Gitea) |
| GET | `/metrics` | Prometheus metrics |

### Ingest Request Schema
```json
{
  "source_type": "git_repo | confluence | url | file",
  "source_url": "http://omni-gitea:3000/omni-admin/my-project.git",
  "collection": "code_embeddings",
  "metadata": {
    "language": "python",
    "project": "my-project"
  },
  "options": {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "embedding_model": "text-embedding-3-small",
    "include_patterns": ["*.py", "*.md"],
    "exclude_patterns": ["*_test.py", "vendor/*"]
  }
}
```

### Example: Ingest Git Repository
```bash
curl -X POST http://omni-knowledge-ingestor:8400/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "git_repo",
    "source_url": "http://omni-gitea:3000/omni-admin/my-project.git",
    "collection": "code_embeddings",
    "metadata": {"language": "python"},
    "options": {
      "chunk_size": 512,
      "include_patterns": ["*.py", "*.md"]
    }
  }'
```

### Example: Batch Ingest
```bash
curl -X POST http://omni-knowledge-ingestor:8400/v1/ingest/batch \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"source_type": "url", "source_url": "https://docs.python.org/3/tutorial/"},
      {"source_type": "url", "source_url": "https://fastapi.tiangolo.com/tutorial/"}
    ],
    "collection": "doc_embeddings",
    "options": {"chunk_size": 1024}
  }'
```

### Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `ingestor_documents_total` | Counter | Total documents ingested |
| `ingestor_chunks_total` | Counter | Total chunks created |
| `ingestor_embeddings_total` | Counter | Total embeddings generated |
| `ingestor_errors_total` | Counter | Ingestion errors |
| `ingestor_latency_seconds` | Histogram | Ingestion latency |

---

## Freshness Monitor — System 19

**Container**: `omni-freshness-monitor` | **Port**: 8401 | **Tier**: Knowledge

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/sources` | List all monitored sources with freshness status |
| GET | `/v1/sources/{id}` | Get source freshness detail |
| POST | `/v1/sources` | Register a new source for monitoring |
| DELETE | `/v1/sources/{id}` | Stop monitoring a source |
| POST | `/v1/sources/{id}/check` | Force freshness check |
| GET | `/v1/stale` | List stale sources needing re-ingestion |
| GET | `/v1/stats` | Monitoring statistics |
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |
| GET | `/metrics` | Prometheus metrics |

### Source Registration Schema
```json
{
  "source_type": "git_repo | url | api",
  "source_url": "http://omni-gitea:3000/omni-admin/my-project.git",
  "check_interval_seconds": 3600,
  "staleness_threshold_seconds": 86400,
  "auto_reingest": true,
  "ingestor_config": {
    "collection": "code_embeddings",
    "chunk_size": 512
  }
}
```

### Example: Register Source
```bash
curl -X POST http://omni-freshness-monitor:8401/v1/sources \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "git_repo",
    "source_url": "http://omni-gitea:3000/omni-admin/my-project.git",
    "check_interval_seconds": 3600,
    "staleness_threshold_seconds": 86400,
    "auto_reingest": true
  }'
```

### Example: List Stale Sources
```bash
curl http://omni-freshness-monitor:8401/v1/stale
```

### Freshness States
| State | Description |
|-------|-------------|
| `fresh` | Source has been checked recently and is up to date |
| `stale` | Source has changed since last ingestion |
| `checking` | Freshness check in progress |
| `reingesting` | Re-ingestion triggered automatically |
| `error` | Last check failed |

---

## Semantic Cache — System 16

**Container**: `omni-semantic-cache` | **Port**: 6380 | **Tier**: Knowledge

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/cache/lookup` | Semantic similarity lookup |
| POST | `/v1/cache/store` | Store a query-response pair |
| DELETE | `/v1/cache/invalidate` | Invalidate cache entries |
| GET | `/v1/cache/stats` | Cache hit/miss statistics |
| POST | `/v1/cache/warm` | Pre-warm cache with entries |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

### Lookup Request
```json
{
  "query": "How to implement circuit breaker in Python",
  "similarity_threshold": 0.92,
  "namespace": "pattern_recommendations",
  "max_results": 1
}
```

### Example: Cache Lookup
```bash
curl -X POST http://omni-semantic-cache:6380/v1/cache/lookup \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Implement retry with exponential backoff",
    "similarity_threshold": 0.92,
    "namespace": "pattern_recommendations"
  }'
```

### Response (Cache Hit)
```json
{
  "hit": true,
  "similarity": 0.97,
  "cached_query": "How to implement retry pattern with exponential backoff",
  "response": { "patterns": ["retry", "circuit-breaker"] },
  "cached_at": "2025-01-01T10:30:00Z",
  "ttl_remaining_seconds": 3200
}
```

### Response (Cache Miss)
```json
{
  "hit": false,
  "similarity": 0.78,
  "closest_query": "Implement retry logic",
  "response": null
}
```

### Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `semantic_cache_hits_total` | Counter | Cache hits |
| `semantic_cache_misses_total` | Counter | Cache misses |
| `semantic_cache_store_total` | Counter | Entries stored |
| `semantic_cache_lookup_latency_seconds` | Histogram | Lookup latency |
| `semantic_cache_entries` | Gauge | Current entry count |

---

## Neo4j Pattern Query API — System 67

**Container**: `omni-neo4j-graphrag-api` | **Port**: 7475 | **Tier**: Knowledge

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/patterns/recommend` | LiteLLM-powered pattern recommendation |
| GET | `/patterns` | List all patterns (optional category filter) |
| GET | `/patterns/{name}` | Full pattern detail with code templates |
| GET | `/patterns/{name}/examples` | Real-world codebase examples |
| GET | `/antipatterns` | List all anti-patterns |
| GET | `/antipatterns/for-task` | Find anti-patterns for a task description |
| GET | `/graph/stats` | Graph node/relationship counts |
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness (checks Neo4j) |
| GET | `/metrics` | Prometheus metrics |

### Recommend Request (POST body)
```json
{
  "task": "Build a REST API with caching and rate limiting",
  "language": "python",
  "limit": 5
}
```

### Example: Recommend Patterns
```bash
curl -X POST http://omni-neo4j-graphrag-api:7475/patterns/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Implement a microservice with database access and retry logic",
    "language": "python",
    "limit": 5
  }'
```

### Example: Get Pattern Detail
```bash
curl http://omni-neo4j-graphrag-api:7475/patterns/circuit-breaker
```

### Example: Graph Stats
```bash
curl http://omni-neo4j-graphrag-api:7475/graph/stats
```

### Response: Pattern Detail
```json
{
  "name": "circuit-breaker",
  "description": "Prevents cascading failures by wrapping calls in a stateful proxy...",
  "category": "Resilience",
  "complexity": "medium",
  "when_to_use": "External service calls, database connections, any I/O that can fail",
  "when_not_to_use": "In-process function calls, local computation",
  "trade_offs": "Adds latency overhead; requires tuning thresholds per dependency",
  "related_patterns": [
    {"name": "retry", "description": "Complements circuit breaker..."},
    {"name": "bulkhead", "description": "Isolates failure domains..."}
  ],
  "anti_patterns": [
    {"name": "infinite-retry", "description": "Retrying forever without backoff..."}
  ],
  "code_templates": {
    "python": "class CircuitBreaker:\n    ...",
    "go": "type CircuitBreaker struct {\n    ..."
  }
}
```

### Metrics
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `pattern_queries_total` | Counter | endpoint, status | Query count by endpoint |
| `pattern_recommendations_total` | Counter | language, status | Recommendation requests |
| `pattern_query_latency_seconds` | Histogram | endpoint | Query latency distribution |

---

*Last updated: 2025-01-01 | All knowledge layer APIs use JSON and expose Prometheus metrics.*
