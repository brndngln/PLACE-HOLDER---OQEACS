# omni-buildgraph-planner

System 9 (Wave B) for the Omni Quantum Elite stack.

- Port: `9802`
- Tier: `CRITICAL`
- Profile: `code-generation`

## Purpose

Build DAG planner and impacted-target analysis service.

## Endpoints

- `POST /api/v1/graph/analyze`
- `POST /api/v1/graph/affected`
- `POST /api/v1/graph/generate-build-files`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
