# omni-fhir-pack

System 31 (Wave E) for the Omni Quantum Elite stack.

- Port: `9867`
- Tier: `HIGH`
- Profile: `domain-packs`

## Purpose

FHIR R4 generator and validation pack.

## Endpoints

- `POST /api/v1/fhir/validate`
- `POST /api/v1/fhir/generate`
- `GET /api/v1/fhir/profiles`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
