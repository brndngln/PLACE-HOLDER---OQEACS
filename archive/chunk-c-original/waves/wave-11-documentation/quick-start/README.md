# Omni Quantum Elite — Quick Start Guide
## 🚀 From Zero to Production in 30 Minutes

---

## Prerequisites

- **Docker** 24+ with Docker Compose v2
- **GPU** (optional): NVIDIA with 24GB+ VRAM for local LLMs
- **RAM**: 32GB minimum, 64GB recommended
- **Storage**: 100GB SSD minimum

---

## 1. Clone & Configure (2 minutes)

```bash
# Clone repository
git clone https://github.com/your-org/omni-quantum-elite.git
cd omni-quantum-elite

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required variables:**
```bash
# Security (CHANGE THESE!)
POSTGRES_PASSWORD=your-secure-password
VAULT_TOKEN=your-vault-token
AUTHENTIK_SECRET_KEY=your-secret-key

# Notifications (optional)
MATTERMOST_WEBHOOK_URL=https://your.mattermost/hooks/xxx
```

---

## 2. Create Network (30 seconds)

```bash
docker network create omni-quantum-network
```

---

## 3. Start Foundation Services (5 minutes)

```bash
# Start data stores
docker-compose -f docker-compose.foundation.yml up -d

# Wait for PostgreSQL
until docker exec omni-postgres pg_isready; do sleep 2; done

# Verify
docker-compose -f docker-compose.foundation.yml ps
```

---

## 4. Start AI Services (10 minutes)

```bash
# Start LLM infrastructure
docker-compose -f docker-compose.ai.yml up -d

# Pull default model (takes a few minutes)
docker exec omni-ollama ollama pull devstral:latest

# Verify
curl http://localhost:11434/api/tags
curl http://localhost:4000/health
```

---

## 5. Start Application Services (5 minutes)

```bash
# Start all application services
docker-compose -f docker-compose.services.yml up -d

# Verify orchestrator
curl http://localhost:9500/health
```

---

## 6. Verify Installation (2 minutes)

```bash
# Run health check
./scripts/health-check.sh

# Or manually check key services
curl http://localhost:9500/health  # Orchestrator
curl http://localhost:4000/health  # LiteLLM
curl http://localhost:6333/readyz  # Qdrant
curl http://localhost:9090/-/healthy  # Prometheus
```

---

## 7. First Request

```bash
curl -X POST http://localhost:9500/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a simple Python function that calculates factorial",
    "model": "devstral:latest"
  }'
```

---

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Orchestrator API | http://localhost:9500 | - |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| Mattermost | http://localhost:8065 | Setup on first visit |
| Portainer | http://localhost:9000 | Setup on first visit |
| Gitea | http://localhost:3001 | Setup on first visit |

---

## Quick Commands

```bash
# Start all services
./scripts/start-all.sh

# Stop all services
./scripts/stop-all.sh

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Restart a service
docker restart omni-<service>
```

---

## Next Steps

1. **Configure Authentik** for SSO
2. **Set up Gitea** repositories
3. **Configure Mattermost** notifications
4. **Import Grafana dashboards** from `/dashboards/`
5. **Read the [Architecture Guide](../architecture/)**

---

## Troubleshooting

**Services won't start?**
```bash
docker-compose logs --tail=50 omni-<service>
```

**Database issues?**
```bash
docker exec omni-postgres pg_isready
```

**AI not responding?**
```bash
curl http://localhost:11434/api/tags
```

See [Troubleshooting Guide](../troubleshooting/) for more.

---

*Omni Quantum Elite v3.0 — Extreme Professional Grade*
