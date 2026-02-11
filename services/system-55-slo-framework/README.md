# omni-slo-framework

System 55 (Wave G) for the Omni Quantum Elite stack.

- Port: `9897`
- Tier: `HIGH`
- Profile: `infrastructure-ops`

## Purpose

SLI/SLO tracking, budgets, and burn-rate alerting service.

## Endpoints

- `GET /api/v1/slo/services`
- `GET /api/v1/slo/{service}/budget`
- `POST /api/v1/slo/{service}/configure`
- `GET /api/v1/slo/alerts`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
