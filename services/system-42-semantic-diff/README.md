# omni-semantic-diff

System 42 (Wave F) for the Omni Quantum Elite stack.

- Port: `9882`
- Tier: `HIGH`
- Profile: `developer-experience`

## Purpose

AST-semantic behavior diff and impact analyzer.

## Endpoints

- `POST /api/v1/diff/semantic`
- `POST /api/v1/diff/impact`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
