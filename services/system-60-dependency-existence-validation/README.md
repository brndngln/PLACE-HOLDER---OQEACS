# System 60 - Dependency Existence Validation

Service codename: dependency-existence-validation

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-60-dependency-existence-validation/docker-compose.yml up -d --build

Default port:
10060
