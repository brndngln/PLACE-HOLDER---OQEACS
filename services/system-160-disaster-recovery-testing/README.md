# System 160 - Disaster Recovery Testing

Service codename: disaster-recovery-testing

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-160-disaster-recovery-testing/docker-compose.yml up -d --build

Default port:
10160
