# omni-elite-mcp-orchestrator

System 68 (Wave G) for the Omni Quantum Elite stack.

- Port: `9913`
- Tier: `HIGH`
- Profile: `infrastructure-ops`

## Purpose

Coordinates MCP service health and routing policies.

## Endpoints

- `POST /api/v1/mcp/route`
- `GET /api/v1/mcp/status`
- `POST /api/v1/mcp/reconcile`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
