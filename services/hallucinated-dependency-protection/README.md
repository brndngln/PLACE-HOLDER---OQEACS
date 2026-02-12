# System 72 - Hallucinated Dependency Protection

Service codename: hallucinated-dependency-protection

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /dependency-check
- GET /metrics

Run:

docker compose -f services/hallucinated-dependency-protection/docker-compose.yml up -d --build

Default port:
8384
