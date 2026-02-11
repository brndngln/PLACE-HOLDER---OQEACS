# omni-redteam-agent

System 7 (Wave A) for the Omni Quantum Elite stack.

- Port: `9857`
- Tier: `CRITICAL`
- Profile: `agent-intelligence`

## Purpose

Automated abuse-case and security payload scanner.

## Endpoints

- `POST /api/v1/redteam/scan`
- `GET /api/v1/redteam/{scan_id}/findings`
- `POST /api/v1/redteam/{scan_id}/retest`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
