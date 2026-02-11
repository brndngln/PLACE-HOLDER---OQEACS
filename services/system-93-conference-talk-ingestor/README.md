# System 93 - Conference Talk Ingestor

Service codename: conference-talk-ingestor

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-93-conference-talk-ingestor/docker-compose.yml up -d --build

Default port:
10093
