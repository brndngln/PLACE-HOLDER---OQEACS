# omni-vuln-graph

System 24 (Wave D) for the Omni Quantum Elite stack.

- Port: `9841`
- Tier: `CRITICAL`
- Profile: `knowledge-intelligence`

## Purpose

Vulnerability feed mirror with dependency risk mapping.

## Endpoints

- `POST /api/v1/vuln/scan`
- `GET /api/v1/vuln/advisory/{cve_id}`
- `POST /api/v1/vuln/sync`
- `GET /api/v1/vuln/stats`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
