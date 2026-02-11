# omni-lineage-explorer

System 41 (Wave F) for the Omni Quantum Elite stack.

- Port: `9881`
- Tier: `HIGH`
- Profile: `developer-experience`

## Purpose

End-to-end lineage graph exploration service.

## Endpoints

- `GET /api/v1/lineage/{task_id}`
- `GET /api/v1/lineage/{task_id}/artifact/{artifact_id}`
- `GET /api/v1/lineage/search`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
