# omni-crypto-harness

System 23 (Wave C) for the Omni Quantum Elite stack.

- Port: `9828`
- Tier: `CRITICAL`
- Profile: `qa-verification`

## Purpose

Crypto KAT execution and misuse detection harness.

## Endpoints

- `POST /api/v1/crypto/verify`
- `GET /api/v1/crypto/vectors/{algorithm}`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
