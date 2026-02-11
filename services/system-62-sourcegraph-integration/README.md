# System 62 - Sourcegraph Integration

Service codename: sourcegraph-integration

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-62-sourcegraph-integration/docker-compose.yml up -d --build

Default port:
10062
