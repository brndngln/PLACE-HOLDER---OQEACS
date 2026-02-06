# Troubleshooting Guide
## Omni Quantum Elite v3.0

---

## Quick Diagnostics

```bash
# System overview
./scripts/health-check.sh

# Check all container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Resource usage
docker stats --no-stream

# Recent logs (all services)
docker-compose logs --tail=50
```

---

## Common Issues

### 1. Services Won't Start

**Symptom:** Container exits immediately or enters restart loop

**Causes & Solutions:**

| Cause | Diagnosis | Solution |
|-------|-----------|----------|
| Missing env vars | `docker logs omni-<service>` shows "missing required" | Add to `.env` file |
| Port conflict | `netstat -tlnp \| grep <port>` | Change port or stop conflicting service |
| Network missing | `docker network ls` | `docker network create omni-quantum-network` |
| Volume permission | `ls -la /var/lib/docker/volumes/` | `chmod -R 777 <volume>` |

### 2. Database Connection Failures

**Symptom:** "Connection refused" or "too many connections"

```bash
# Check PostgreSQL
docker exec omni-postgres pg_isready

# Check connection count
docker exec omni-postgres psql -U fortress -c "SELECT count(*) FROM pg_stat_activity;"

# Check PgBouncer
docker exec omni-pgbouncer psql -p 6432 -U pgbouncer_admin pgbouncer -c "SHOW POOLS;"
```

**Solutions:**
- Restart PgBouncer: `docker restart omni-pgbouncer`
- Increase max connections in `postgresql.conf`
- Check for connection leaks in application code

### 3. LLM Response Timeouts

**Symptom:** Requests to `/chat/completions` timeout

```bash
# Check Ollama
curl http://omni-ollama:11434/api/tags

# Check LiteLLM
curl http://omni-litellm:4000/health

# Check GPU
nvidia-smi
```

**Solutions:**
- Restart Ollama: `docker restart omni-ollama`
- Reduce context length in request
- Check VRAM usage and unload unused models
- Increase timeout in client

### 4. High Memory Usage

**Symptom:** Services OOM killed, system swapping

```bash
# Find memory hogs
docker stats --no-stream --format "{{.Name}}: {{.MemUsage}}" | sort -k2 -h

# Check swap
swapon --show
free -h
```

**Solutions:**
- Set memory limits in docker-compose
- Restart high-memory services
- Clear caches: `docker exec omni-redis redis-cli FLUSHALL`
- Reduce batch sizes in AI workloads

### 5. Vector Search Slow

**Symptom:** Qdrant queries take >1 second

```bash
# Check collection stats
curl http://omni-qdrant:6333/collections/<name>

# Check cluster status
curl http://omni-qdrant:6333/cluster
```

**Solutions:**
- Create HNSW index if missing
- Reduce search limit
- Add payload index for filtered queries
- Increase Qdrant resources

### 6. Deployment Failures

**Symptom:** Blue-green or canary deployment fails

```bash
# Check deployment status
curl http://omni-blue-green:9650/api/v1/deployments

# Check health aggregator
curl http://omni-health-aggregator:9653/api/v1/health
```

**Solutions:**
- Check target container health endpoint
- Verify image exists and is accessible
- Check Traefik configuration
- Manual rollback if needed

### 7. Notifications Not Working

**Symptom:** No messages in Mattermost

```bash
# Test webhook
curl -X POST $MATTERMOST_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"text":"Test message"}'
```

**Solutions:**
- Verify webhook URL is correct
- Check Mattermost channel permissions
- Verify notifier service is running

---

## Diagnostic Commands

```bash
# Full system diagnostics
docker-compose ps
docker-compose logs --tail=20
docker stats --no-stream
df -h
free -h

# Network diagnostics
docker network inspect omni-quantum-network
docker exec omni-<service> curl -v http://omni-<other>:<port>/health

# Database diagnostics
docker exec omni-postgres psql -U fortress -c "\l"
docker exec omni-postgres psql -U fortress -c "\dt"
docker exec omni-redis redis-cli INFO memory

# AI diagnostics
curl http://omni-ollama:11434/api/tags | jq
curl http://omni-litellm:4000/model/info | jq
```

---

## Getting Help

1. Check logs: `docker logs --tail=100 omni-<service>`
2. Search this guide
3. Check runbooks in `/docs/runbooks/`
4. Post in Mattermost #help channel

---

*Last Updated: 2024-01-01*
