# System 65 - Context Compiler

Service codename: context-compiler

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-65-context-compiler/docker-compose.yml up -d --build

Default port:
10065
