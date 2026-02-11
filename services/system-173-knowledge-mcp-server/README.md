# System 173 - Knowledge Mcp Server

Service codename: knowledge-mcp-server

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-173-knowledge-mcp-server/docker-compose.yml up -d --build

Default port:
10173
