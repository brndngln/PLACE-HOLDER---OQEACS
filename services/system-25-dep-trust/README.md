# omni-dep-trust

System 25 (Wave D) for the Omni Quantum Elite stack.

- Port: `9842`
- Tier: `HIGH`
- Profile: `knowledge-intelligence`

## Purpose

Dependency trust scorer with policy threshold enforcement.

## Endpoints

- `POST /api/v1/trust/score`
- `POST /api/v1/trust/batch`
- `GET /api/v1/trust/policy`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
