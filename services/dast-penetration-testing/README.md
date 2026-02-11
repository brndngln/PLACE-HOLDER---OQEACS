# System 67 - DAST Penetration Testing (ZAP)

Service codename: dast-penetration-testing

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /dast
- GET /metrics

Run:

docker compose -f services/dast-penetration-testing/docker-compose.yml up -d --build

Default port:
8090
