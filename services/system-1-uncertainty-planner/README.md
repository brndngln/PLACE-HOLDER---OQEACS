# omni-uncertainty-planner

System 1 (Wave A) for the Omni Quantum Elite stack.

- Port: `9851`
- Tier: `CRITICAL`
- Profile: `agent-intelligence`

## Purpose

Confidence scoring and escalation planner for autonomous operations.

## Endpoints

- `POST /api/v1/plan/evaluate`
- `POST /api/v1/plan/calibrate`
- `GET /api/v1/plan/thresholds`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
