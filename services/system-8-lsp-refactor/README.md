# omni-lsp-refactor

System 8 (Wave B) for the Omni Quantum Elite stack.

- Port: `9801`
- Tier: `CRITICAL`
- Profile: `code-generation`

## Purpose

Semantic refactoring orchestration via language-server protocol operations.

## Endpoints

- `POST /api/v1/refactor/rename`
- `POST /api/v1/refactor/extract-function`
- `POST /api/v1/refactor/references`
- `GET /api/v1/servers/status`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
