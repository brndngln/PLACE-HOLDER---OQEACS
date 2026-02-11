# omni-contract-synth

System 11 (Wave B) for the Omni Quantum Elite stack.

- Port: `9804`
- Tier: `HIGH`
- Profile: `code-generation`

## Purpose

Contract and SDK synthesis for OpenAPI/Proto/AsyncAPI.

## Endpoints

- `POST /api/v1/contracts/openapi`
- `POST /api/v1/contracts/protobuf`
- `POST /api/v1/contracts/validate`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
