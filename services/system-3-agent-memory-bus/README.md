# omni-agent-memory-bus

System 3 (Wave A) for the Omni Quantum Elite stack.

- Port: `9853`
- Tier: `HIGH`
- Profile: `agent-intelligence`

## Purpose

Conflict-resistant shared scratchpad and event stream for parallel agents.

## Endpoints

- `POST /api/v1/sessions`
- `GET /api/v1/sessions/{id}`
- `PUT /api/v1/sessions/{id}/write`
- `GET /api/v1/sessions/{id}/subscribe`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
