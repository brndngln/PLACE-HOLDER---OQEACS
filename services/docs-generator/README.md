# Documentation Generator

System 11/14 of the Omni Quantum Elite Generation Intelligence Layer.

## Service
- Name: `omni-docs-generator`
- Port: `9629`
- Critical: `false`

## Run
```bash
docker compose -f docker-compose.yml up -d --build
```

## Endpoints
- `GET /health`
- `GET /ready`
- `GET /metrics`
- `GET /info`
- `GET /docs`
