# omni-elite-chaos-guard

System 71 (Wave G) for the Omni Quantum Elite stack.

- Port: `9916`
- Tier: `HIGH`
- Profile: `infrastructure-ops`

## Purpose

Controlled chaos experiment scheduler with automatic safety rollback.

## Endpoints

- `POST /api/v1/chaos/start`
- `GET /api/v1/chaos/{id}/status`
- `POST /api/v1/chaos/{id}/stop`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
