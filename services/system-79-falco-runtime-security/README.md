# System 79 - Falco Runtime Security

Service codename: falco-runtime-security

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-79-falco-runtime-security/docker-compose.yml up -d --build

Default port:
10079
