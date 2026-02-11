# System 52 - Code Completion (Tabby ML)

Service codename: code-completion-tabby

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /completions
- GET /metrics

Run:

docker compose -f services/code-completion-tabby/docker-compose.yml up -d --build

Default port:
8320
