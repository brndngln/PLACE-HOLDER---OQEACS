# System 171 - Test Mcp Server

Service codename: test-mcp-server

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-171-test-mcp-server/docker-compose.yml up -d --build

Default port:
10171
