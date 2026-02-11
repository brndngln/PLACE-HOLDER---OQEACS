# omni-elite-release-readiness

System 72 (Wave G) for the Omni Quantum Elite stack.

- Port: `9917`
- Tier: `CRITICAL`
- Profile: `infrastructure-ops`

## Purpose

Release readiness scorer aggregating quality, security, and SLO posture.

## Endpoints

- `POST /api/v1/release/evaluate`
- `GET /api/v1/release/{id}/status`
- `GET /api/v1/release/{id}/gates`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
