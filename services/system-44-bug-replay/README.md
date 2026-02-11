# omni-bug-replay

System 44 (Wave F) for the Omni Quantum Elite stack.

- Port: `9884`
- Tier: `MEDIUM`
- Profile: `developer-experience`

## Purpose

Deterministic execution record/replay manager.

## Endpoints

- `POST /api/v1/replay/record`
- `POST /api/v1/replay/play`
- `GET /api/v1/replay/recordings`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
