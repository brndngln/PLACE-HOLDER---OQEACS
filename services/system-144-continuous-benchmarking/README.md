# System 144 - Continuous Benchmarking

Service codename: continuous-benchmarking

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-144-continuous-benchmarking/docker-compose.yml up -d --build

Default port:
10144
