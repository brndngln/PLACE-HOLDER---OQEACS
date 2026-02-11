# System 64 - Clean Room Reproducibility

Service codename: clean-room-reproducibility

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-64-clean-room-reproducibility/docker-compose.yml up -d --build

Default port:
10064
