# System 48B — Real-Time API Intelligence

Monitors dependencies for update risk, breaking changes, compatibility issues, and security advisories.

## Endpoints
- `POST /api/v1/scan`
- `GET /api/v1/packages/{name}`
- `GET /api/v1/packages/{name}/changes`
- `POST /api/v1/upgrade-plan`
- `GET /api/v1/compatibility/{pkg_a}/{pkg_b}`
- `POST /api/v1/compatibility/matrix`
- `GET /health`
- `GET /metrics`

## Run
```bash
docker compose up -d --build
```

## Test
```bash
pytest -q
```
