# Runbook: Scaling

## Overview
Procedures for scaling Omni Quantum Elite services to handle increased load or optimize resource usage.

**Audience**: Platform engineers, DevOps
**Estimated time**: 15–60 minutes
**Risk level**: Medium

---

## Scaling Strategies

| Strategy | When to Use | Services |
|----------|-------------|----------|
| **Vertical** (increase resources) | Single instance bottleneck | Neo4j, PostgreSQL, Ollama |
| **Horizontal** (add instances) | Stateless services under load | LiteLLM, GraphRAG API, Knowledge Ingestor |
| **Caching** (reduce load) | Repeated queries, high read load | Semantic Cache, Redis |
| **Offloading** (external services) | GPU/compute limits | LiteLLM → cloud models |

---

## Identifying Bottlenecks

### Key Metrics to Watch

```promql
# CPU usage per container
rate(container_cpu_usage_seconds_total[5m])

# Memory usage per container
container_memory_usage_bytes / container_spec_memory_limit_bytes

# Request rate per service
rate(http_requests_total[5m])

# Error rate per service
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Response latency p99
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

### Quick Diagnostic

```bash
# Container resource usage
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Network connections per container
for c in $(docker ps --format "{{.Names}}"); do
    count=$(docker exec $c ss -tun 2>/dev/null | wc -l || echo "N/A")
    echo "${c}: ${count} connections"
done
```

---

## Vertical Scaling Procedures

### Increase Container Memory

Edit `docker-compose.yml`:
```yaml
services:
  omni-neo4j:
    deploy:
      resources:
        limits:
          memory: 8g    # Increase from 4g
        reservations:
          memory: 4g    # Increase from 2g
```

Apply:
```bash
docker compose up -d omni-neo4j
```

### Increase Neo4j Heap

```yaml
environment:
  - NEO4J_server_memory_heap_max__size=4g     # was 2g
  - NEO4J_server_memory_pagecache_size=2g     # was 1g
```

```bash
docker compose restart omni-neo4j
```

### Increase PostgreSQL Resources

```yaml
environment:
  - POSTGRES_SHARED_BUFFERS=2GB       # was 512MB
  - POSTGRES_EFFECTIVE_CACHE_SIZE=6GB # was 2GB
  - POSTGRES_WORK_MEM=256MB          # was 64MB
  - POSTGRES_MAX_CONNECTIONS=200      # was 100
```

### Increase Qdrant Resources

```yaml
environment:
  - QDRANT__STORAGE__OPTIMIZERS__MEMMAP_THRESHOLD=50000  # was 20000
  - QDRANT__STORAGE__PERFORMANCE__MAX_SEARCH_THREADS=8   # was 4
```

---

## Horizontal Scaling Procedures

### Scale Stateless API Services

For services that can run multiple instances behind a load balancer:

```yaml
# docker-compose.yml
services:
  omni-neo4j-graphrag-api:
    # ... existing config ...
    deploy:
      replicas: 3
```

```bash
docker compose up -d --scale omni-neo4j-graphrag-api=3
```

Traefik automatically load-balances between replicas when they're on the same network.

### Scale LiteLLM Proxy

```bash
docker compose up -d --scale omni-litellm=2
```

Configure Traefik for sticky sessions (important for streaming):
```yaml
labels:
  - "traefik.http.services.litellm.loadbalancer.sticky.cookie=true"
  - "traefik.http.services.litellm.loadbalancer.sticky.cookie.name=litellm_session"
```

### Scale Knowledge Ingestor

```bash
docker compose up -d --scale omni-knowledge-ingestor=2
```

Ensure ingestion tasks are distributed (use Redis queue for task coordination):
```yaml
environment:
  - REDIS_URL=redis://omni-redis:6379/1
  - WORKER_MODE=true
```

---

## Caching Strategies

### Increase Semantic Cache Hit Rate

```bash
# Check current hit rate
curl http://omni-semantic-cache:6380/v1/cache/stats

# Lower similarity threshold (more hits, less precision)
# In semantic-cache config:
SIMILARITY_THRESHOLD=0.88  # was 0.92

# Increase cache TTL
CACHE_TTL_SECONDS=7200  # was 3600

# Pre-warm cache with common queries
curl -X POST http://omni-semantic-cache:6380/v1/cache/warm \
  -d '{
    "entries": [
      {"query": "implement singleton pattern", "response": {...}},
      {"query": "circuit breaker pattern python", "response": {...}}
    ]
  }'
```

### Add Redis Caching to API Services

For frequently-read, rarely-changed data (e.g., pattern listings):
```python
import redis.asyncio as redis

cache = redis.from_url("redis://omni-redis:6379/0")

async def get_patterns_cached():
    cached = await cache.get("patterns:all")
    if cached:
        return json.loads(cached)
    patterns = await fetch_patterns_from_neo4j()
    await cache.setex("patterns:all", 300, json.dumps(patterns))  # 5 min TTL
    return patterns
```

---

## Load Testing

### Basic Load Test with curl

```bash
# Pattern recommendation throughput
for i in $(seq 1 100); do
    curl -sf -X POST http://omni-neo4j-graphrag-api:7475/patterns/recommend \
      -H "Content-Type: application/json" \
      -d '{"task": "build REST API with caching", "limit": 5}' \
      -o /dev/null -w "%{http_code} %{time_total}s\n" &
done
wait
```

### Using hey (HTTP load generator)

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Test pattern recommendation endpoint
hey -n 1000 -c 50 -m POST \
  -H "Content-Type: application/json" \
  -d '{"task": "implement retry pattern", "limit": 5}' \
  http://localhost:7475/patterns/recommend

# Test pattern listing endpoint
hey -n 5000 -c 100 http://localhost:7475/patterns
```

### Interpreting Results

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| p50 latency | < 50ms | 50–200ms | > 200ms |
| p99 latency | < 500ms | 500ms–2s | > 2s |
| Error rate | < 0.1% | 0.1–1% | > 1% |
| Throughput | > 100 rps | 50–100 rps | < 50 rps |

---

## Auto-Scaling (Future)

For Kubernetes-based deployments, apply HPA:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: graphrag-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: omni-neo4j-graphrag-api
  minReplicas: 2
  maxReplicas: 8
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

---

## Capacity Planning

### Current Resource Usage (Baseline)

Run this to establish a baseline:

```bash
#!/usr/bin/env bash
echo "=== Capacity Baseline $(date) ==="
echo ""
echo "--- Container Resources ---"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
echo ""
echo "--- Disk Usage ---"
docker system df -v
echo ""
echo "--- GPU Usage ---"
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv 2>/dev/null || echo "No GPU"
```

### Growth Projections

| Metric | Current | +50% Load | +100% Load | Action |
|--------|---------|-----------|------------|--------|
| Pattern queries/min | 20 | 30 | 40 | Scale GraphRAG API to 2 replicas |
| LLM requests/min | 50 | 75 | 100 | Scale LiteLLM to 2 replicas |
| Qdrant points | 125K | 187K | 250K | Monitor memory, add storage |
| PostgreSQL connections | 50 | 75 | 100 | Increase max_connections |
| Neo4j heap | 2 GB | 3 GB | 4 GB | Increase heap allocation |

---

## Scaling Decision Tree

```
Is the service CPU-bound?
├── Yes → Increase CPU limit or add replicas
└── No
    Is the service memory-bound?
    ├── Yes → Increase memory limit
    └── No
        Is the service I/O-bound?
        ├── Yes → Add caching layer or optimize queries
        └── No
            Is the service network-bound?
            ├── Yes → Check connection limits, add load balancing
            └── No
                Profile the application for specific bottlenecks
```
