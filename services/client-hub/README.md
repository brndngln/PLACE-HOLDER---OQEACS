# Client Communication Hub

System 12/14 of the Omni Quantum Elite Generation Intelligence Layer.

## Service
- Name: `omni-client-hub`
- Port: `9630`
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
