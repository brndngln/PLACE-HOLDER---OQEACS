# System 54 - Quality Gate Engine

Service codename: quality-gate-engine

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-54-quality-gate-engine/docker-compose.yml up -d --build

Default port:
10054
