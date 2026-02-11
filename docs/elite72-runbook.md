# Elite 72 Runbook

## Overview
This runbook covers deployment, health verification, metrics checks, and operational actions for the 72 elite services.

## Prerequisites
- Docker + Docker Compose v2
- Docker network `omni-quantum-network`
- Existing core infra containers (Postgres, Redis, Qdrant, LiteLLM, etc.)

## Deploy
```bash
./deploy-elite-72.sh
```

Optional wave-only deploy:
```bash
DEPLOY_WAVE_A=true DEPLOY_WAVE_B=false DEPLOY_WAVE_C=false \
DEPLOY_WAVE_D=false DEPLOY_WAVE_E=false DEPLOY_WAVE_F=false \
DEPLOY_WAVE_G=false ./deploy-elite-72.sh
```

## Health Checks
Quick spot check:
```bash
curl -fsS http://localhost:9851/health
```

Full stack report:
```bash
cat reports/elite72-health-report.md
```

## Metrics
Sample metrics endpoint:
```bash
curl -fsS http://localhost:9851/metrics | head
```

Full metrics report:
```bash
cat reports/elite72-metrics-report.md
```

## Logs
```bash
docker logs --tail 100 omni-uncertainty-planner
```

## Restart / Rollback
Restart a single service:
```bash
docker restart omni-uncertainty-planner
```

Rebuild and restart a wave:
```bash
docker compose -f docker-compose.elite-72.yml --profile agent-intelligence up -d --build
```

## Cleanup
Stop a wave:
```bash
docker compose -f docker-compose.elite-72.yml --profile agent-intelligence down
```

Stop everything:
```bash
docker compose -f docker-compose.elite-72.yml --profile all down
```

## Troubleshooting
- If a service is `unhealthy`, check:
  - `docker inspect --format '{{.State.Health}}' <container>`
  - `docker logs --tail 200 <container>`
- If host `curl` works but container is unhealthy, ensure the container healthcheck can reach `localhost:{PORT}`.
- For permission issues, verify Docker socket access for the current user.
