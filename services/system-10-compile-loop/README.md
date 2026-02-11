# omni-compile-loop

System 10 (Wave B) for the Omni Quantum Elite stack.

- Port: `9803`
- Tier: `CRITICAL`
- Profile: `code-generation`

## Purpose

Compile-feedback loop with structured diagnostics.

## Endpoints

- `POST /api/v1/compile`
- `GET /api/v1/compile/stats`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
