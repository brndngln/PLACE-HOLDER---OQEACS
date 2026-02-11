# System 78 - Threat Modeling Agent

Service codename: threat-modeling-agent

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-78-threat-modeling-agent/docker-compose.yml up -d --build

Default port:
10078
