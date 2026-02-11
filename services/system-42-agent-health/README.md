# System 42 -- Agent Health Monitor

Continuous health monitoring for AI coding agents in the Omni Quantum
Elite platform.  Runs poison-pill security tests, golden-test quality
suites, performance drift detection, A/B prompt comparisons, and full
agent benchmarks.

## Purpose

| Capability | Description |
|---|---|
| Poison Pills | Six exploit-style prompts (SQL injection, XSS, race condition, hardcoded secret, unbounded query, missing error handling) that a healthy agent must refuse or mitigate. |
| Golden Tests | Five canonical prompts (CRUD API, auth system, WebSocket chat, background worker, CLI tool) scored against expected code patterns. |
| Drift Detection | 7-day rolling average over historical scores; alerts via Mattermost when decline exceeds 10 %. |
| A/B Testing | Compare two system prompts against the same test cases and declare a winner. |
| Benchmarking | Run all sub-systems and produce a single 0..1 overall score. |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness / readiness probe |
| `GET` | `/metrics` | Prometheus scrape endpoint |
| `GET` | `/api/v1/agents` | List known agents |
| `GET` | `/api/v1/agents/{id}/health` | Health summary for one agent |
| `GET` | `/api/v1/agents/{id}/history` | Performance history (last N days) |
| `POST` | `/api/v1/poison-pill/run?agent_id=` | Trigger poison-pill suite |
| `GET` | `/api/v1/poison-pill/results` | Retrieve stored results |
| `POST` | `/api/v1/golden-tests/run?agent_id=` | Trigger golden-test suite |
| `GET` | `/api/v1/golden-tests/results` | Retrieve stored results |
| `GET` | `/api/v1/drift-report?agent_id=` | Drift report |
| `POST` | `/api/v1/ab-test` | Start A/B prompt test |
| `GET` | `/api/v1/ab-test/{id}` | Retrieve A/B result |
| `POST` | `/api/v1/benchmark?agent_id=` | Full agent benchmark |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SERVICE_NAME` | `agent-health` | Service identifier |
| `SERVICE_PORT` | `9635` | Listening port |
| `LOG_LEVEL` | `INFO` | structlog level |
| `DATABASE_URL` | `postgresql+asyncpg://omni:omni@omni-postgres:5432/omni_agent_health` | asyncpg connection string |
| `REDIS_URL` | `redis://omni-redis:6379/8` | Redis URL |
| `LITELLM_URL` | `http://omni-litellm:4000` | LiteLLM proxy for agent prompts |
| `MATTERMOST_WEBHOOK_URL` | `http://omni-mattermost:8065/hooks/agent-health` | Alert webhook |
| `SANDBOX_URL` | `http://omni-sandbox:9620` | Code execution sandbox |

## Scheduled Jobs

| Schedule | Job |
|---|---|
| Daily 03:00 UTC | Poison-pill sweep (all agents) |
| Weekly Sunday 04:00 UTC | Golden-test run (all agents) |
| Every hour | Drift detection (all agents) |

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server (connects to local/dev Postgres + Redis)
uvicorn src.main:app --host 0.0.0.0 --port 9635 --reload
```

## Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

## Docker

```bash
docker compose up --build -d
```

## Integration Notes

- Prompts are sent to agents via the **LiteLLM** proxy (`/v1/chat/completions`).
- Performance history is read from the `agent_performance_history` table in PostgreSQL.
- Critical failures trigger immediate **Mattermost** alerts.
- Prometheus metrics are available at `/metrics` for Grafana dashboards.
- The service runs in degraded mode when Postgres or Redis are unavailable (health endpoint still returns 200).
