# omni-spec-clarifier

System 6 (Wave A) for the Omni Quantum Elite stack.

- Port: `9856`
- Tier: `HIGH`
- Profile: `agent-intelligence`

## Purpose

Ambiguity detector and clarifying-question generator.

## Endpoints

- `POST /api/v1/clarify`
- `POST /api/v1/clarify/answer`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
