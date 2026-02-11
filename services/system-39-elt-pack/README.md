# omni-elt-pack

System 39 (Wave E) for the Omni Quantum Elite stack.

- Port: `9870`
- Tier: `MEDIUM`
- Profile: `domain-packs`

## Purpose

ELT and warehouse modeling project generator.

## Endpoints

- `POST /api/v1/elt/generate`
- `POST /api/v1/elt/validate`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
