# System 69 - Mcp Db Schema Server

Service codename: mcp-db-schema-server

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-69-mcp-db-schema-server/docker-compose.yml up -d --build

Default port:
10069
