# omni-k8s-target

System 49 (Wave G) for the Omni Quantum Elite stack.

- Port: `9891`
- Tier: `CRITICAL`
- Profile: `infrastructure-ops`

## Purpose

Kubernetes target generator and deployment validator.

## Endpoints

- `POST /api/v1/k8s/generate-helm`
- `POST /api/v1/k8s/generate-kustomize`
- `POST /api/v1/k8s/validate`
- `POST /api/v1/k8s/deploy`

## Health and Metrics

- `GET /health`
- `GET /metrics`

## Integration

Designed for internal calls over `omni-quantum-network` using container DNS names.
