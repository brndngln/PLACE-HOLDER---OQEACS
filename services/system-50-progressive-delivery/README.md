# omni-progressive-delivery

System 50 (Wave G) for the Omni Quantum Elite stack.

- Port: `9892`
- Tier: `CRITICAL`
- Profile: `infrastructure-ops`

## Purpose

Weighted rollout and auto-rollback orchestration.

## Endpoints

- `POST /api/v1/rollout/start`
- `GET /api/v1/rollout/{id}/status`
- `POST /api/v1/rollout/{id}/promote`
- `POST /api/v1/rollout/{id}/rollback`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
