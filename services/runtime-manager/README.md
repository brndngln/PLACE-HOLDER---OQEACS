# Language Runtime Manager

System 4/14 of the Omni Quantum Elite Generation Intelligence Layer.

## Service
- Name: `omni-runtime-manager`
- Port: `9624`
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
