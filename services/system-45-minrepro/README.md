# omni-minrepro

System 45 (Wave F) for the Omni Quantum Elite stack.

- Port: `9885`
- Tier: `HIGH`
- Profile: `developer-experience`

## Purpose

Delta-debugging minimizer for failing scenarios.

## Endpoints

- `POST /api/v1/repro/minimize`
- `GET /api/v1/repro/{id}/result`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
