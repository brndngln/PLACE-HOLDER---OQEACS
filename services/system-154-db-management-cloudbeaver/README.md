# System 154 - Db Management Cloudbeaver

Service codename: db-management-cloudbeaver

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-154-db-management-cloudbeaver/docker-compose.yml up -d --build

Default port:
10154
