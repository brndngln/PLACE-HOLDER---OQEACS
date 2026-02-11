# System 61 - Architecture Rule Enforcement

Service codename: architecture-rule-enforcement

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-61-architecture-rule-enforcement/docker-compose.yml up -d --build

Default port:
10061
