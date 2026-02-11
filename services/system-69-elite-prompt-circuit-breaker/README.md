# omni-elite-prompt-circuit-breaker

System 69 (Wave A) for the Omni Quantum Elite stack.

- Port: `9914`
- Tier: `HIGH`
- Profile: `agent-intelligence`

## Purpose

Circuit breaker for prompt loops, over-tokening, and unsafe retries.

## Endpoints

- `POST /api/v1/circuit/evaluate`
- `POST /api/v1/circuit/open`
- `GET /api/v1/circuit/state`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
