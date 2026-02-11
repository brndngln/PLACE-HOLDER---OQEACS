# omni-mesh-identity

System 51 (Wave G) for the Omni Quantum Elite stack.

- Port: `9893`
- Tier: `CRITICAL`
- Profile: `infrastructure-ops`

## Purpose

Zero-trust service identity and policy generator.

## Endpoints

- `POST /api/v1/mesh/generate-identity`
- `POST /api/v1/mesh/generate-policy`
- `GET /api/v1/mesh/topology`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
