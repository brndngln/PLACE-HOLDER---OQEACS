# System 132 - Error Tracking Glitchtip

Service codename: error-tracking-glitchtip

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-132-error-tracking-glitchtip/docker-compose.yml up -d --build

Default port:
10132
