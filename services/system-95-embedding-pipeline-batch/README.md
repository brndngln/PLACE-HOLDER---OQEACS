# System 95 - Embedding Pipeline Batch

Service codename: embedding-pipeline-batch

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-95-embedding-pipeline-batch/docker-compose.yml up -d --build

Default port:
10095
