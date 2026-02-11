# Observability OTel

OpenTelemetry control plane for Omni Quantum Elite with collector health checks, instrumentation validation, and sampling policy controls.

## Endpoints
- `GET /api/v1/pipelines`
- `GET /api/v1/pipelines/sampling`
- `PUT /api/v1/pipelines/sampling`
- `POST /api/v1/instrumentation/check`
- `GET /api/v1/collector/status`

Infra:
- `/health`, `/ready`, `/metrics`, `/info`

## Collector
Collector config is in `config/otel-collector.yaml` and exposes:
- OTLP gRPC `4317`
- OTLP HTTP `4318`
- Health endpoint `13133` (mapped to host `9656`)
