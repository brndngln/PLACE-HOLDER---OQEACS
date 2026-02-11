# System 72 - Prompt Decay Detector

Service codename: prompt-decay-detector

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-72-prompt-decay-detector/docker-compose.yml up -d --build

Default port:
10072
