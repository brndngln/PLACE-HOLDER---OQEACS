# Temporal Orchestrator

Temporal control plane service for Omni Quantum Elite. This system adds durable workflow orchestration primitives and a service API for workflow definitions, run control, signaling, and termination.

## Endpoints
- `POST /api/v1/workflows/definitions`
- `GET /api/v1/workflows/definitions`
- `POST /api/v1/workflows/runs`
- `GET /api/v1/workflows/runs`
- `GET /api/v1/workflows/runs/{run_id}`
- `POST /api/v1/workflows/runs/{run_id}/signal`
- `POST /api/v1/workflows/runs/{run_id}/terminate`
- `GET /api/v1/workflows/stats`

Infra endpoints:
- `/health`
- `/ready`
- `/metrics`
- `/info`

## Notes
- Compose includes Temporal server (`omni-temporal`) and UI (`omni-temporal-ui`).
- API supports controlled simulated execution mode while integrating with real Temporal workflows incrementally.
