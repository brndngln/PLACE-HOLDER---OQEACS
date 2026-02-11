# Policy Engine

OPA-backed policy decision system for Omni Quantum Elite. It provides centralized policy authoring, validation, and runtime decision APIs.

## Endpoints
- `POST /api/v1/policies`
- `GET /api/v1/policies`
- `GET /api/v1/policies/{policy_id}`
- `POST /api/v1/decisions/{policy_id}`
- `POST /api/v1/bundles/validate`
- `GET /api/v1/opa/status`

Infra:
- `/health`, `/ready`, `/metrics`, `/info`

## Rego Notes
- `package_path` must match the `package` declaration inside Rego.
- Decisions are evaluated via OPA when `OPA_SYNC_ENABLED=true`; local fallback mode is also available.
