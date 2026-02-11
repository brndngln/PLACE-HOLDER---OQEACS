# omni-native-fuzz-cluster

System 21 (Wave C) for the Omni Quantum Elite stack.

- Port: `9826`
- Tier: `HIGH`
- Profile: `qa-verification`

## Purpose

Coverage-guided native fuzzing and crash corpus manager.

## Endpoints

- `POST /api/v1/fuzz/native/start`
- `GET /api/v1/fuzz/native/{job_id}/crashes`
- `POST /api/v1/fuzz/native/{job_id}/minimize`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
