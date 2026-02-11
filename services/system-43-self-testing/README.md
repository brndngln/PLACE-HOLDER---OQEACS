# System 43: Self-Testing System

Platform self-testing engine for the Omni Quantum Elite AI Coding System. Runs integration tests against all platform services to verify they are operating correctly. Integrates with GI-1 Execution Sandbox (`omni-sandbox:9620`) for isolated test execution and GI-4 Quality Scoring (`omni-scoring:9623`) for scoring.

**Container:** `omni-self-test` | **Port:** `9636` | **Tier:** CRITICAL

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/metrics` | Prometheus metrics |
| `POST` | `/api/v1/run` | Trigger full test suite (health + integration) |
| `GET` | `/api/v1/results` | List latest suite results |
| `GET` | `/api/v1/results/{id}` | Retrieve a specific suite result |
| `POST` | `/api/v1/run/health` | Run health checks only |
| `POST` | `/api/v1/run/integration` | Run integration suite only |
| `GET` | `/api/v1/report` | Get platform health report |
| `GET` | `/api/v1/services` | List all monitored services |

## Scheduled Jobs

| Schedule | Job |
|----------|-----|
| Every 5 minutes | Health check sweep across all services |
| Every hour | Full integration test suite |
| Daily 06:00 UTC | Comprehensive platform health report |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `self-testing` | Service identifier |
| `SERVICE_PORT` | `9636` | Listen port |
| `DATABASE_URL` | `postgresql+asyncpg://omni:omni@omni-postgres:5432/omni_self_testing` | Postgres connection |
| `REDIS_URL` | `redis://omni-redis:6379/9` | Redis connection |
| `MATTERMOST_WEBHOOK_URL` | `http://omni-mattermost:8065/hooks/self-testing` | Mattermost alerts |
| `SANDBOX_URL` | `http://omni-sandbox:9620` | GI-1 Execution Sandbox |
| `SCORING_URL` | `http://omni-scoring:9623` | GI-4 Quality Scoring |
| `RETROSPECTIVE_URL` | `http://omni-retrospective:9633` | Retrospective service |

## Monitored Services

The following 20 services are actively monitored:

| Service | URL | Health Endpoint |
|---------|-----|-----------------|
| omni-postgres | `omni-postgres:5432` | `/` |
| omni-redis | `omni-redis:6379` | `/` |
| omni-qdrant | `omni-qdrant:6333` | `/healthz` |
| omni-litellm | `omni-litellm:4000` | `/health` |
| omni-prometheus | `omni-prometheus:9090` | `/-/healthy` |
| omni-grafana | `omni-grafana:3000` | `/api/health` |
| omni-loki | `omni-loki:3100` | `/ready` |
| omni-mattermost | `omni-mattermost:8065` | `/api/v4/system/ping` |
| omni-vault | `omni-vault:8200` | `/v1/sys/health` |
| omni-gitea | `omni-gitea:3000` | `/api/healthz` |
| omni-n8n | `omni-n8n:5678` | `/healthz` |
| omni-langfuse | `omni-langfuse:3000` | `/api/public/health` |
| omni-traefik | `omni-traefik:8080` | `/ping` |
| omni-orchestrator | `omni-orchestrator:9637` | `/health` |
| omni-context-compiler | `omni-context-compiler:8100` | `/health` |
| omni-freshness | `omni-freshness:8200` | `/health` |
| omni-agent-health | `omni-agent-health:9635` | `/health` |
| omni-formal-verify | `omni-formal-verify:9634` | `/health` |
| omni-minio | `omni-minio:9000` | `/minio/health/live` |
| omni-ollama | `omni-ollama:11434` | `/api/tags` |

## Running Locally

```bash
docker compose up --build
```

## Running Tests

```bash
pip install -r requirements.txt pytest pytest-asyncio httpx
pytest tests/ -v
```
