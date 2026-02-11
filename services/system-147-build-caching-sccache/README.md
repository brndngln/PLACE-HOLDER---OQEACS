# System 147 - Build Caching Sccache

Service codename: build-caching-sccache

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-147-build-caching-sccache/docker-compose.yml up -d --build

Default port:
10147
