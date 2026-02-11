# System 53 - Code Scorer Service

Service codename: code-scorer-service

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-53-code-scorer-service/docker-compose.yml up -d --build

Default port:
10053
