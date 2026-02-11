# omni-tool-policy

System 4 (Wave A) for the Omni Quantum Elite stack.

- Port: `9854`
- Tier: `HIGH`
- Profile: `agent-intelligence`

## Purpose

Contextual policy optimizer for selecting tool sequences.

## Endpoints

- `POST /api/v1/policy/recommend`
- `POST /api/v1/policy/feedback`
- `GET /api/v1/policy/stats`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
