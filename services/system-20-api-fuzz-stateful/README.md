# omni-api-fuzz-stateful

System 20 (Wave C) for the Omni Quantum Elite stack.

- Port: `9825`
- Tier: `HIGH`
- Profile: `qa-verification`

## Purpose

Stateful OpenAPI fuzzing job orchestration.

## Endpoints

- `POST /api/v1/fuzz/start`
- `GET /api/v1/fuzz/{job_id}/status`
- `GET /api/v1/fuzz/{job_id}/findings`
- `GET /api/v1/fuzz/{job_id}/regression-tests`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
