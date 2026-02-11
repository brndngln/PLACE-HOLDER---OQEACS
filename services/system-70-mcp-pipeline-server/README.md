# System 70 - Mcp Pipeline Server

Service codename: mcp-pipeline-server

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-70-mcp-pipeline-server/docker-compose.yml up -d --build

Default port:
10070
