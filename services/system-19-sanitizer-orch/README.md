# omni-sanitizer-orch

System 19 (Wave C) for the Omni Quantum Elite stack.

- Port: `9824`
- Tier: `CRITICAL`
- Profile: `qa-verification`

## Purpose

Runtime sanitizer matrix execution controller.

## Endpoints

- `POST /api/v1/sanitize/run`
- `GET /api/v1/sanitize/matrix`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
