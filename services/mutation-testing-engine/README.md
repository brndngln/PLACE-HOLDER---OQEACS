# System 46 - Mutation Testing Engine

Service codename: mutation-testing-engine

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /mutations
- GET /metrics

Run:

docker compose -f services/mutation-testing-engine/docker-compose.yml up -d --build

Default port:
9646
