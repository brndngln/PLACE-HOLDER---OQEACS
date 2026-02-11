# omni-admission-guard

System 52 (Wave G) for the Omni Quantum Elite stack.

- Port: `9894`
- Tier: `HIGH`
- Profile: `infrastructure-ops`

## Purpose

Deployment policy validation and admission control rules.

## Endpoints

- `POST /api/v1/guard/validate`
- `GET /api/v1/guard/policies`
- `POST /api/v1/guard/add-policy`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
