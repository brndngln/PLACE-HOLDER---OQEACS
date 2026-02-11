# System 140 - Semantic Cache

Service codename: semantic-cache

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-140-semantic-cache/docker-compose.yml up -d --build

Default port:
10140
