# System 116 - Swe Bench Integration

Service codename: swe-bench-integration

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-116-swe-bench-integration/docker-compose.yml up -d --build

Default port:
10116
