# System 120 - Jepsen Distributed Testing

Service codename: jepsen-distributed-testing

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-120-jepsen-distributed-testing/docker-compose.yml up -d --build

Default port:
10120
