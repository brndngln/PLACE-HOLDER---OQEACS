# System 86 - Knowledge Ingestor

Service codename: knowledge-ingestor

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-86-knowledge-ingestor/docker-compose.yml up -d --build

Default port:
10086
