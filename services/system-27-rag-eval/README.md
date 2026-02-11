# omni-rag-eval

System 27 (Wave D) for the Omni Quantum Elite stack.

- Port: `9844`
- Tier: `HIGH`
- Profile: `knowledge-intelligence`

## Purpose

Continuous retrieval quality and groundedness evaluator.

## Endpoints

- `POST /api/v1/eval/run`
- `POST /api/v1/eval/add-pair`
- `GET /api/v1/eval/history`
- `GET /api/v1/eval/alerts`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
