# System 62 - Architecture Diagram Generation

Service codename: architecture-diagram-generation

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /diagrams
- GET /metrics

Run:

docker compose -f services/architecture-diagram-generation/docker-compose.yml up -d --build

Default port:
8379
