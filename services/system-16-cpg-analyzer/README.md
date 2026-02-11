# omni-cpg-analyzer

System 16 (Wave C) for the Omni Quantum Elite stack.

- Port: `9821`
- Tier: `HIGH`
- Profile: `qa-verification`

## Purpose

Code property graph analysis endpoint wrapper.

## Endpoints

- `POST /api/v1/cpg/analyze`
- `POST /api/v1/cpg/query`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
