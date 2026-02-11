# System 47B — Semantic Code Understanding Engine

Builds semantic graphs for repositories and provides change impact analysis.

## Endpoints
- `POST /api/v1/analyze`
- `GET /api/v1/graph/{repo_id}`
- `POST /api/v1/meaning`
- `POST /api/v1/impact`
- `GET /api/v1/entities/{entity_id}/dependents`
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
