# omni-iot-pack

System 35 (Wave E) for the Omni Quantum Elite stack.

- Port: `9861`
- Tier: `MEDIUM`
- Profile: `domain-packs`

## Purpose

Firmware and simulation pack for MCU targets.

## Endpoints

- `POST /api/v1/iot/generate`
- `POST /api/v1/iot/simulate`
- `POST /api/v1/iot/validate`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
