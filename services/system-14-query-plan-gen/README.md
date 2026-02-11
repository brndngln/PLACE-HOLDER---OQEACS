# omni-query-plan-gen

System 14 (Wave B) for the Omni Quantum Elite stack.

- Port: `9807`
- Tier: `HIGH`
- Profile: `code-generation`

## Purpose

Query plan inspection with index and ORM rewrite recommendations.

## Endpoints

- `POST /api/v1/analyze/query`
- `POST /api/v1/analyze/orm`
- `POST /api/v1/suggest/indexes`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
