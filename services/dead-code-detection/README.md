# System 57 - Dead Code Detection

Service codename: dead-code-detection

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /dead-code
- GET /metrics

Run:

docker compose -f services/dead-code-detection/docker-compose.yml up -d --build

Default port:
9657
