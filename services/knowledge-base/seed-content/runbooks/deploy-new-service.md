# Runbook: Deploy a New Service

## Overview
Step-by-step procedure for adding a new service to the Omni Quantum Elite platform.

**Audience**: Platform engineers, DevOps
**Estimated time**: 30–60 minutes
**Risk level**: Medium

---

## Prerequisites

- [ ] Docker Compose access on the host
- [ ] Gitea admin or org-member credentials
- [ ] Vault token with `secret/data/omni/*` write access
- [ ] Authentik admin access (if service needs SSO)

---

## Procedure

### Step 1 — Create the Service Repository

```bash
# Create repo in Gitea
curl -X POST http://omni-gitea:3000/api/v1/orgs/omni-admin/repos \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-new-service",
    "description": "Description of the service",
    "private": true,
    "auto_init": true,
    "default_branch": "main"
  }'
```

### Step 2 — Store Secrets in Vault

```bash
# Write service secrets
curl -X POST http://omni-vault:8200/v1/secret/data/omni/my-new-service \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -d '{
    "data": {
      "db_password": "generated_secure_password",
      "api_key": "sk-generated-key"
    }
  }'
```

### Step 3 — Create the Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -sf http://localhost:8080/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Step 4 — Add to Docker Compose

Add the service block to `docker-compose.yml`:

```yaml
  omni-my-new-service:
    build:
      context: ./services/my-new-service
      dockerfile: Dockerfile
    container_name: omni-my-new-service
    restart: unless-stopped
    ports:
      - "8XXX:8080"
    environment:
      - SERVICE_NAME=my-new-service
      - LOG_LEVEL=info
      - VAULT_ADDR=http://omni-vault:8200
      - VAULT_TOKEN=${VAULT_TOKEN}
    networks:
      - omni-quantum-network
    labels:
      omni.quantum.component: my-new-service
      omni.quantum.tier: <tier>
    depends_on:
      omni-vault:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

### Step 5 — Implement Required Endpoints

Every service must implement:

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness probe (returns 200 if process is alive) |
| `GET /ready` | Readiness probe (returns 200 if dependencies are connected) |
| `GET /metrics` | Prometheus metrics in exposition format |

Recommended libraries:
- **Python**: FastAPI + structlog + prometheus_client
- **Go**: chi/gin + zap + prometheus/client_golang
- **TypeScript**: Fastify + pino + prom-client

### Step 6 — Configure Prometheus Scraping

Add the service to Prometheus configuration:

```yaml
# prometheus/prometheus.yml
scrape_configs:
  - job_name: 'my-new-service'
    static_configs:
      - targets: ['omni-my-new-service:8080']
    metrics_path: /metrics
    scrape_interval: 15s
```

### Step 7 — Configure Traefik Routing (if externally accessible)

Add Traefik labels to the Docker Compose service:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.my-new-service.rule=Host(`my-new-service.omni.local`)"
  - "traefik.http.routers.my-new-service.entrypoints=websecure"
  - "traefik.http.routers.my-new-service.tls=true"
  - "traefik.http.services.my-new-service.loadbalancer.server.port=8080"
```

### Step 8 — Configure Authentik SSO (if needed)

1. Create application in Authentik admin panel
2. Create OAuth2/OIDC provider with redirect URI
3. Configure service with OIDC credentials from Vault

### Step 9 — Deploy

```bash
# Build and start the new service
docker compose up -d --build omni-my-new-service

# Verify health
curl http://localhost:8XXX/health

# Check logs
docker logs -f omni-my-new-service
```

### Step 10 — Register with Knowledge Base

1. Add service to the platform-overview wiki page
2. Create API reference documentation
3. Register as source in Knowledge Ingestor (if it has docs/code to ingest)

```bash
curl -X POST http://omni-knowledge-ingestor:8400/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "git_repo",
    "source_url": "http://omni-gitea:3000/omni-admin/my-new-service.git",
    "collection": "code_embeddings"
  }'
```

---

## Verification Checklist

- [ ] Service container starts without errors
- [ ] `/health` returns 200
- [ ] `/ready` returns 200
- [ ] `/metrics` returns Prometheus-format metrics
- [ ] Prometheus is scraping the service (check Targets page)
- [ ] Grafana dashboard shows the new service
- [ ] Traefik routing works (if applicable)
- [ ] Secrets are in Vault (not in env files or code)
- [ ] Service is documented in Wiki.js
- [ ] Backup strategy defined (persistent volumes added to Duplicati)

---

## Rollback

```bash
# Stop the service
docker compose stop omni-my-new-service

# Remove the container
docker compose rm -f omni-my-new-service

# Revert docker-compose.yml changes
git checkout docker-compose.yml
```

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Container exits immediately | Check logs: `docker logs omni-my-new-service` |
| Cannot connect to Vault | Verify VAULT_ADDR and VAULT_TOKEN environment variables |
| Service not in Prometheus targets | Restart Prometheus after config change |
| Traefik not routing | Verify labels and that the service is on `omni-quantum-network` |
| Health check failing | Ensure the health endpoint is accessible inside the container |
