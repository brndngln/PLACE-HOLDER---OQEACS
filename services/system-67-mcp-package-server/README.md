# System 67 - Mcp Package Server

Service codename: mcp-package-server

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-67-mcp-package-server/docker-compose.yml up -d --build

Default port:
10067
