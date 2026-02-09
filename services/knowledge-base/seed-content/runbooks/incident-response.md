# Runbook: Incident Response

## Overview
Standardized procedure for responding to platform incidents affecting the Omni Quantum Elite system.

**Audience**: All engineers, on-call responders
**Estimated time**: Varies by severity
**Risk level**: High

---

## Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| **SEV-1** | Platform down, all users affected | < 15 min | Full network failure, orchestrator crash |
| **SEV-2** | Major feature broken, many users affected | < 30 min | LiteLLM down, Neo4j unreachable |
| **SEV-3** | Minor feature degraded, workaround exists | < 2 hours | Slow cache, single dashboard broken |
| **SEV-4** | Cosmetic or low-impact issue | Next business day | UI glitch, non-critical log errors |

---

## Incident Response Procedure

### Phase 1 — Detection and Triage (0–15 min)

1. **Acknowledge the alert** in Grafana/Alertmanager or communication channel
2. **Assess severity** using the table above
3. **Create incident channel** in Rocket.Chat: `#incident-YYYY-MM-DD-brief-desc`
4. **Assign roles**:
   - **Incident Commander (IC)**: Coordinates response, communicates status
   - **Technical Lead**: Investigates root cause and implements fix
   - **Communicator**: Updates stakeholders

### Phase 2 — Diagnosis (15–45 min)

#### Quick Health Assessment
```bash
# Check all service health
for svc in omni-litellm omni-qdrant omni-neo4j omni-neo4j-graphrag-api \
           omni-token-infinity omni-knowledge-ingestor omni-freshness-monitor \
           omni-semantic-cache omni-wikijs omni-grafana; do
    echo -n "${svc}: "
    curl -sf "http://${svc}:$(docker inspect --format='{{range $p, $conf := .NetworkSettings.Ports}}{{(index $conf 0).HostPort}}{{end}}' ${svc} 2>/dev/null)/health" \
      && echo "OK" || echo "FAIL"
done
```

#### Check Container Status
```bash
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

#### Check Recent Logs
```bash
# Last 100 lines from a specific service
docker logs --tail 100 omni-<service-name>

# Search for errors across all services
docker compose logs --tail 50 | grep -i "error\|fatal\|panic"
```

#### Check Resource Usage
```bash
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
```

#### Check Grafana Dashboards
- Platform Overview: `http://omni-grafana:3000/d/platform-overview`
- Service Health: `http://omni-grafana:3000/d/service-health`
- LLM Usage: `http://omni-grafana:3000/d/llm-usage`

#### Check Langfuse (for AI/LLM issues)
- Traces: `http://omni-langfuse:3000/traces`
- Check for elevated error rates or latency spikes

### Phase 3 — Mitigation (Immediate Actions)

#### Restart a Service
```bash
docker compose restart omni-<service-name>
# Wait for health check
sleep 10
curl -sf http://omni-<service-name>:<port>/health
```

#### Scale Down (Remove Load)
```bash
# Temporarily disable Traefik routing to a service
docker compose exec omni-traefik traefik healthcheck --ping
```

#### Failover to Backup (if available)
```bash
# Example: Switch LiteLLM to backup model
curl -X POST http://omni-litellm:4000/model/update \
  -H "Authorization: Bearer ${LITELLM_ADMIN_KEY}" \
  -d '{"model_id": "primary-gpt4", "enabled": false}'
```

#### Database Recovery
```bash
# Check PostgreSQL
docker exec omni-postgres pg_isready -U postgres

# Check Neo4j
docker exec omni-neo4j cypher-shell -u neo4j -p quantum_elite_2024 "RETURN 1"

# Check Redis
docker exec omni-redis redis-cli ping
```

### Phase 4 — Resolution

1. **Implement fix** (code change, config update, or infrastructure adjustment)
2. **Verify fix** by checking health endpoints and key functionality
3. **Monitor** for 30 minutes to confirm stability
4. **Update incident channel** with resolution summary

### Phase 5 — Post-Incident

1. **Close incident channel** with final status
2. **Write incident report** using the [Incident Report Template](/templates/incident-report)
3. **Schedule post-mortem** within 48 hours for SEV-1 and SEV-2
4. **Create follow-up tickets** for preventive measures
5. **Update runbooks** if new failure modes were discovered

---

## Common Failure Scenarios

### Neo4j Unreachable
```bash
# Check container
docker logs --tail 50 omni-neo4j
# Check memory (Neo4j is memory-intensive)
docker stats --no-stream omni-neo4j
# Restart if needed
docker compose restart omni-neo4j
# Verify seed data is intact
docker exec omni-neo4j cypher-shell -u neo4j -p quantum_elite_2024 \
  "MATCH (p:Pattern) RETURN count(p)"
```

### LiteLLM Proxy Errors
```bash
# Check API key validity
curl http://omni-litellm:4000/v1/models \
  -H "Authorization: Bearer ${LITELLM_API_KEY}"
# Check upstream provider status
curl http://omni-litellm:4000/health
# Restart proxy
docker compose restart omni-litellm
```

### Qdrant Out of Memory
```bash
# Check collection sizes
curl http://omni-qdrant:6333/collections
# Optimize collections (compact segments)
curl -X POST http://omni-qdrant:6333/collections/code_embeddings/index
# If critical, increase memory limit in docker-compose.yml
```

### Wiki.js Not Loading
```bash
docker logs --tail 50 omni-wikijs
# Check database connection
docker exec omni-postgres psql -U postgres -d wikijs -c "SELECT 1"
# Restart
docker compose restart omni-wikijs
```

---

## Escalation Path

1. **On-call engineer**: First responder, handles SEV-3/4
2. **Senior engineer**: Escalation for SEV-2
3. **Platform lead**: Escalation for SEV-1
4. **External support**: Vendor support for infrastructure issues

---

## Communication Templates

### Initial Alert
> **[SEV-X] Incident: Brief description**
> Detected at: HH:MM UTC
> Impact: What is affected
> Status: Investigating
> IC: @name

### Status Update
> **[SEV-X] Update: Brief description**
> Status: Mitigating / Monitoring
> Actions taken: What was done
> ETA: When we expect resolution

### Resolution
> **[SEV-X] Resolved: Brief description**
> Resolved at: HH:MM UTC
> Duration: X hours Y minutes
> Root cause: Brief explanation
> Follow-up: Post-mortem scheduled for DATE
