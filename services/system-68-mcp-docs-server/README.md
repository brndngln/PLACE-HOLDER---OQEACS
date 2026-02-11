# System 68 - Mcp Docs Server

Service codename: mcp-docs-server

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-68-mcp-docs-server/docker-compose.yml up -d --build

Default port:
10068
