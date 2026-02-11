# omni-desktop-pack

System 37 (Wave E) for the Omni Quantum Elite stack.

- Port: `9865`
- Tier: `MEDIUM`
- Profile: `domain-packs`

## Purpose

Desktop app packaging, signing, and update channel pack.

## Endpoints

- `POST /api/v1/desktop/generate`
- `POST /api/v1/desktop/build`
- `POST /api/v1/desktop/sign`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
