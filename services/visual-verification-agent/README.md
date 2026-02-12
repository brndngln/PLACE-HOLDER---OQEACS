# System 71 - Visual Verification Agent

Service codename: visual-verification-agent

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /visual-verify
- GET /metrics

Run:

docker compose -f services/visual-verification-agent/docker-compose.yml up -d --build

Default port:
8383
