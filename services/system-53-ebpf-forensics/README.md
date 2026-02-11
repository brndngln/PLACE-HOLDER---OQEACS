# omni-ebpf-forensics

System 53 (Wave G) for the Omni Quantum Elite stack.

- Port: `9895`
- Tier: `HIGH`
- Profile: `infrastructure-ops`

## Purpose

Runtime anomaly event and forensic alert stream.

## Endpoints

- `POST /api/v1/ebpf/deploy-policy`
- `GET /api/v1/ebpf/events`
- `GET /api/v1/ebpf/alerts`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
