# System 128 - Email Service Listmonk

Service codename: email-service-listmonk

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-128-email-service-listmonk/docker-compose.yml up -d --build

Default port:
10128
