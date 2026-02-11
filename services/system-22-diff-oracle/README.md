# omni-diff-oracle

System 22 (Wave C) for the Omni Quantum Elite stack.

- Port: `9827`
- Tier: `HIGH`
- Profile: `qa-verification`

## Purpose

Golden-traffic behavior diff runner.

## Endpoints

- `POST /api/v1/diff/record`
- `POST /api/v1/diff/compare`
- `GET /api/v1/diff/{report_id}/details`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
