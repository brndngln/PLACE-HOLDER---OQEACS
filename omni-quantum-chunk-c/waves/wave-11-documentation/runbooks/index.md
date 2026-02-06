# Omni Quantum Elite — Runbook Collection
## Version 3.0.0

---

## Quick Links

| Runbook | Description | Severity |
|---------|-------------|----------|
| [Service Down](#service-down) | Restart failed services | SEV-2 |
| [High Memory](#high-memory) | Memory pressure mitigation | SEV-3 |
| [Database Issues](#database-issues) | PostgreSQL troubleshooting | SEV-1 |
| [LLM Failures](#llm-failures) | AI model issues | SEV-2 |
| [Deployment Rollback](#deployment-rollback) | Revert bad deploys | SEV-2 |

---

## Service Down

### Symptoms
- Health check failures
- 5xx errors from service
- Service not responding to requests

### Diagnosis
```bash
# Check container status
docker ps -a | grep omni-<service>

# Check logs
docker logs --tail 100 omni-<service>

# Check resource usage
docker stats omni-<service> --no-stream
```

### Resolution
```bash
# Restart service
docker restart omni-<service>

# If restart fails, recreate
docker-compose -f docker-compose.<service>.yml up -d --force-recreate

# Verify health
curl http://omni-<service>:<port>/health
```

### Escalation
If service doesn't recover after 3 restart attempts, escalate to SEV-1.

---

## High Memory

### Symptoms
- Container OOM killed
- Slow response times
- Swap usage increasing

### Diagnosis
```bash
# Check memory by container
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check system memory
free -h

# Check for memory leaks
docker exec omni-<service> ps aux --sort=-%mem | head
```

### Resolution
```bash
# Restart high-memory container
docker restart omni-<service>

# Increase memory limit (temporary)
docker update --memory=2g omni-<service>

# Clear caches
docker exec omni-redis redis-cli FLUSHDB
```

---

## Database Issues

### Symptoms
- Connection timeouts
- Slow queries
- Replication lag

### Diagnosis
```bash
# Check connections
docker exec omni-postgres psql -U fortress -c "SELECT count(*) FROM pg_stat_activity;"

# Check slow queries
docker exec omni-postgres psql -U fortress -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Check locks
docker exec omni-postgres psql -U fortress -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

### Resolution
```bash
# Kill long-running queries
docker exec omni-postgres psql -U fortress -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE duration > interval '5 minutes';"

# Restart connections via PgBouncer
docker restart omni-pgbouncer

# Emergency: Restart PostgreSQL
docker restart omni-postgres
```

---

## LLM Failures

### Symptoms
- Timeout errors from LiteLLM
- Model loading failures
- Out of VRAM errors

### Diagnosis
```bash
# Check Ollama status
curl http://omni-ollama:11434/api/tags

# Check LiteLLM health
curl http://omni-litellm:4000/health

# Check GPU memory
nvidia-smi
```

### Resolution
```bash
# Restart Ollama
docker restart omni-ollama

# Clear model cache
docker exec omni-ollama rm -rf /root/.ollama/models/blobs/*

# Reload specific model
curl -X POST http://omni-ollama:11434/api/pull -d '{"name":"devstral:latest"}'
```

---

## Deployment Rollback

### Symptoms
- New deployment causing errors
- Performance regression
- Feature not working

### Steps
```bash
# 1. Check current deployment
curl http://omni-rollback:9652/api/v1/current/<service>

# 2. Trigger rollback
curl -X POST http://omni-rollback:9652/api/v1/rollback \
  -H "Content-Type: application/json" \
  -d '{"service":"<service>","reason":"Performance regression"}'

# 3. Verify rollback
curl http://omni-<service>:<port>/health

# 4. Notify team
curl -X POST $MATTERMOST_WEBHOOK_URL \
  -d '{"text":"🔄 Rollback complete for <service>"}'
```

---

## Contact

- **Primary On-Call:** Brendan
- **Escalation:** Create incident in Mattermost #incidents

---

*Last Updated: 2024-01-01*
