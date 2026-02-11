# System 49 — Execution Verification Loop

Runs generated code in a constrained sandbox, executes tests, and iteratively regenerates fixes until code is verified or retry limits are reached.

## Endpoints
- `POST /api/v1/verify` full verification loop
- `POST /api/v1/execute` single execution
- `GET /api/v1/results/{id}` stored verification result
- `POST /api/v1/generate-tests` auto-generate tests
- `POST /api/v1/run-tests` run explicit tests
- `GET /health` liveness
- `GET /metrics` Prometheus metrics

## Run
```bash
cp .env.example .env
docker compose up -d
```
