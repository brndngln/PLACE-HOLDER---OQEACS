# System 80 - Provenance Signing

Service codename: provenance-signing

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-80-provenance-signing/docker-compose.yml up -d --build

Default port:
10080
