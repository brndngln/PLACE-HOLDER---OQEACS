# System 77 - Iac Linting

Service codename: iac-linting

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-77-iac-linting/docker-compose.yml up -d --build

Default port:
10077
