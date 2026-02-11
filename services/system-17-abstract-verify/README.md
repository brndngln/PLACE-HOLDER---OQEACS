# omni-abstract-verify

System 17 (Wave C) for the Omni Quantum Elite stack.

- Port: `9822`
- Tier: `HIGH`
- Profile: `qa-verification`

## Purpose

Abstract interpretation and proof result orchestrator.

## Endpoints

- `POST /api/v1/verify/eva`
- `POST /api/v1/verify/wp`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
