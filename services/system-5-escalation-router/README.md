# omni-escalation-router

System 5 (Wave A) for the Omni Quantum Elite stack.

- Port: `9855`
- Tier: `HIGH`
- Profile: `agent-intelligence`

## Purpose

Stall and failure detector with reroute recommendations.

## Endpoints

- `POST /api/v1/monitor/register`
- `GET /api/v1/monitor/{task_id}/status`
- `POST /api/v1/monitor/{task_id}/resolve`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
