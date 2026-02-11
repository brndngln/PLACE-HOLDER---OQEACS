# omni-migration-diff

System 26 (Wave D) for the Omni Quantum Elite stack.

- Port: `9843`
- Tier: `HIGH`
- Profile: `knowledge-intelligence`

## Purpose

Release note parser producing structured migration rules.

## Endpoints

- `POST /api/v1/migration/ingest`
- `GET /api/v1/migration/check`
- `POST /api/v1/migration/sync`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
