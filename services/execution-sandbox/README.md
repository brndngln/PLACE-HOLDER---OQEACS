# Agent Execution Sandbox

System 1/14 of the Omni Quantum Elite Generation Intelligence Layer.

## Service
- Name: `omni-execution-sandbox`
- Port: `9620`
- Critical: `true`

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
