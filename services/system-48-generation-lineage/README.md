# omni-generation-lineage

System 48 (Wave F) for the Omni Quantum Elite stack.

- Port: `9888`
- Tier: `HIGH`
- Profile: `developer-experience`

## Purpose

Prompt-level generation lineage and retrieval trace service.

## Endpoints

- `POST /api/v1/generation-lineage/register`
- `GET /api/v1/generation-lineage/{task_id}`
- `GET /api/v1/generation-lineage/search`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
