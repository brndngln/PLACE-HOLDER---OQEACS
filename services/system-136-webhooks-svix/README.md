# System 136 - Webhooks Svix

Service codename: webhooks-svix

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-136-webhooks-svix/docker-compose.yml up -d --build

Default port:
10136
