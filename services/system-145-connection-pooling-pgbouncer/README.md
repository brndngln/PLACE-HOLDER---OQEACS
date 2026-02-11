# System 145 - Connection Pooling Pgbouncer

Service codename: connection-pooling-pgbouncer

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-145-connection-pooling-pgbouncer/docker-compose.yml up -d --build

Default port:
10145
