# System 45 - Knowledge Freshness Service

**Container:** `omni-freshness` | **Port:** `8361` | **Tier:** CRITICAL

Monitors the software ecosystem for breaking changes, deprecations, security advisories, and best practices. Scores relevance with AI via LiteLLM, stores high-value updates in Qdrant for retrieval-augmented generation, and alerts the team through Mattermost.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check with subsystem status |
| `GET` | `/metrics` | Prometheus-compatible metrics |
| `GET` | `/api/v1/feeds` | List all configured feeds (built-in + custom) |
| `POST` | `/api/v1/feeds` | Add a custom feed source |
| `GET` | `/api/v1/updates` | Retrieve recent knowledge updates from Qdrant |
| `GET` | `/api/v1/updates/breaking` | Retrieve breaking change updates |
| `POST` | `/api/v1/updates/scan` | Trigger an immediate full feed scan |
| `GET` | `/api/v1/deprecations` | List tracked deprecation warnings |
| `GET` | `/api/v1/report` | Get or generate the weekly freshness report |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `knowledge-freshness` | Service identifier |
| `SERVICE_PORT` | `8361` | HTTP port |
| `DATABASE_URL` | `postgresql+asyncpg://omni:omni@omni-postgres:5432/omni_freshness` | PostgreSQL connection string |
| `REDIS_URL` | `redis://omni-redis:6379/10` | Redis connection string |
| `QDRANT_URL` | `http://omni-qdrant:6333` | Qdrant vector store URL |
| `LITELLM_URL` | `http://omni-litellm:4000` | LiteLLM AI gateway URL |
| `MATTERMOST_WEBHOOK_URL` | `http://omni-mattermost-webhook:8066` | Mattermost incoming webhook |
| `SCAN_INTERVAL_HOURS` | `6` | Hours between full feed scans |
| `SECURITY_SCAN_INTERVAL_HOURS` | `1` | Hours between security advisory scans |
| `GITHUB_TOKEN` | *(empty)* | GitHub PAT to increase API rate limits |
| `LOG_LEVEL` | `INFO` | Logging level |

## Feed Categories

### GitHub Releases (20 repositories)

fastapi, pydantic, react, next.js, django, flask, go, rust, TypeScript, node, cpython, compose, kubernetes, terraform, grafana, prometheus, langchain, transformers, ruff, uv

### Security Advisories

- GitHub Security Advisories
- NVD CVE Feed
- CISA Advisories

### Framework Changelogs

- Python Insider
- Node.js Blog
- Rust Blog
- Go Blog
- TypeScript Blog

### Best Practices (Tech Blogs)

- Netflix Tech Blog
- Cloudflare Blog
- Stripe Engineering
- GitHub Engineering
- Uber Engineering

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Full Feed Scan | Every 6 hours | Scans all feed categories, scores with AI, stores in Qdrant |
| Security Scan | Every 1 hour | Scans security advisory feeds with lower relevance threshold |
| Weekly Report | Monday 09:00 UTC | Generates aggregate freshness report and notifies Mattermost |

## Integration Notes

- **Qdrant:** Updates with `relevance_score >= 0.7` are embedded via LiteLLM and stored. Deduplication uses cosine similarity threshold of 0.95.
- **LiteLLM:** Used for both text embeddings (`text-embedding-ada-002`) and classification scoring (`gpt-4o-mini`).
- **PostgreSQL:** Stores deprecation warning records with ON CONFLICT upsert.
- **Redis:** Caches the latest scan report (24h TTL) and weekly report (7d TTL).
- **Mattermost:** Breaking changes, deprecations, security advisories, and weekly summaries are sent as formatted webhook messages.

## Running Locally

```bash
# Copy environment file
cp .env.example .env

# Build and start
docker compose up --build -d

# Check health
curl http://localhost:8361/health

# Trigger a manual scan
curl -X POST http://localhost:8361/api/v1/updates/scan
```

## Running Tests

```bash
pip install -r requirements.txt pytest pytest-asyncio
python -m pytest tests/ -v
```

## Architecture

```
src/
  config.py           # Pydantic Settings configuration
  models.py           # Pydantic v2 data models
  main.py             # FastAPI app with lifespan, routers, metrics
  routers/
    feeds.py          # Feed management endpoints
    updates.py        # Update listing and scan trigger
    reports.py        # Deprecation and weekly report endpoints
  services/
    feed_parser.py    # RSS/Atom/GitHub release parsing
    scorer.py         # AI-powered relevance scoring via LiteLLM
    freshness.py      # Core orchestration: scan, store, alert
    scheduler.py      # APScheduler job definitions
  utils/
    notifications.py  # Mattermost webhook helper
tests/
  conftest.py         # Shared pytest fixtures
  test_health.py      # Health and metrics endpoint tests
  test_feed_parser.py # Feed parser unit tests
  test_freshness.py   # Freshness service and model tests
```
