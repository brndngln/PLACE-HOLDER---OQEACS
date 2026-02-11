# omni-preview-env

System 46 (Wave F) for the Omni Quantum Elite stack.

- Port: `9886`
- Tier: `HIGH`
- Profile: `developer-experience`

## Purpose

Branch-scoped preview environment lifecycle manager.

## Endpoints

- `POST /api/v1/preview/create`
- `GET /api/v1/preview/{id}/status`
- `DELETE /api/v1/preview/{id}`
- `GET /api/v1/preview/active`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
