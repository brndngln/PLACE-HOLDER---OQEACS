# System 64 - Distributed Tracing (Jaeger)

Service codename: distributed-tracing-jaeger

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /traces
- GET /metrics

Run:

docker compose -f services/distributed-tracing-jaeger/docker-compose.yml up -d --build

Default port:
16686
