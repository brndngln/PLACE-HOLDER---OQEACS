# omni-patch-tree

System 2 (Wave A) for the Omni Quantum Elite stack.

- Port: `9852`
- Tier: `HIGH`
- Profile: `agent-intelligence`

## Purpose

Patch search tree with branch scoring, pruning, and checkpoint awareness.

## Endpoints

- `POST /api/v1/search/start`
- `GET /api/v1/search/{id}/status`
- `GET /api/v1/search/{id}/best-patch`
- `POST /api/v1/search/{id}/prune`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
