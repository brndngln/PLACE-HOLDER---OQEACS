# System 172 - Deploy Mcp Server

Service codename: deploy-mcp-server

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-172-deploy-mcp-server/docker-compose.yml up -d --build

Default port:
10172
