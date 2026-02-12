# System 54 - Database Design Intelligence

Service codename: database-design-intelligence

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /schema-check
- GET /metrics

Run:

docker compose -f services/database-design-intelligence/docker-compose.yml up -d --build

Default port:
8336
