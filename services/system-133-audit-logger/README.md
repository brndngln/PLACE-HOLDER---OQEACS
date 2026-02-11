# System 133 - Audit Logger

Service codename: audit-logger

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-133-audit-logger/docker-compose.yml up -d --build

Default port:
10133
