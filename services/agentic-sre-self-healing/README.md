# System 58 - Agentic SRE Self-Healing

Service codename: agentic-sre-self-healing

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /self-heal
- GET /metrics

Run:

docker compose -f services/agentic-sre-self-healing/docker-compose.yml up -d --build

Default port:
8377
