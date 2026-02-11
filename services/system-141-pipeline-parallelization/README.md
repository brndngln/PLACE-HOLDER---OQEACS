# System 141 - Pipeline Parallelization

Service codename: pipeline-parallelization

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-141-pipeline-parallelization/docker-compose.yml up -d --build

Default port:
10141
