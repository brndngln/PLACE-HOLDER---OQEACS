# omni-repro-miner

System 30 (Wave D) for the Omni Quantum Elite stack.

- Port: `9847`
- Tier: `HIGH`
- Profile: `knowledge-intelligence`

## Purpose

Automatic minimal reproducible failure extractor.

## Endpoints

- `POST /api/v1/repro/minimize`
- `GET /api/v1/repro/{id}/status`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
