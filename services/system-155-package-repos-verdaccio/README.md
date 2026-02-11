# System 155 - Package Repos Verdaccio

Service codename: package-repos-verdaccio

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-155-package-repos-verdaccio/docker-compose.yml up -d --build

Default port:
10155
