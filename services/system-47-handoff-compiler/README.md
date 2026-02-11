# omni-handoff-compiler

System 47 (Wave F) for the Omni Quantum Elite stack.

- Port: `9887`
- Tier: `HIGH`
- Profile: `developer-experience`

## Purpose

Client-ready handoff bundle assembler.

## Endpoints

- `POST /api/v1/handoff/generate`
- `GET /api/v1/handoff/{id}/download`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
