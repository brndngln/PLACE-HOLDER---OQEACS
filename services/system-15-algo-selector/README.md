# omni-algo-selector

System 15 (Wave B) for the Omni Quantum Elite stack.

- Port: `9808`
- Tier: `MEDIUM`
- Profile: `code-generation`

## Purpose

Microbenchmark-driven implementation selector.

## Endpoints

- `POST /api/v1/benchmark/run`
- `GET /api/v1/benchmark/history`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
