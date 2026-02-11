# System 44 -- MCP Servers

Model Context Protocol (MCP) servers for the Omni Quantum Elite AI Coding System.
Provides four specialised tool servers that AI coding agents can query for code
analysis, test generation, deployment management, and knowledge-base lookups.

## Architecture

```
Port 8335  +-----------------+   LiteLLM   +-------------+
 --------->| MCP Analysis    |------------>| omni-litellm|
           +-----------------+   Qdrant    +-------------+
                                 ------->  | omni-qdrant |
Port 8336  +-----------------+             +-------------+
 --------->| MCP Test        |------------>|
           +-----------------+             |
                                           |
Port 8337  +-----------------+   Coolify   +-------------+
 --------->| MCP Deploy      |------------>| omni-coolify|
           +-----------------+             +-------------+
                                           |
Port 8338  +-----------------+   Qdrant    |
 --------->| MCP Knowledge   |------------>|
           +-----------------+             +-------------+
```

## Servers

### MCP Analysis Server (port 8335)

Container: `omni-mcp-analysis`

| Tool | Description |
|------|-------------|
| `analyze_code` | LLM-powered comprehensive code review with severity-rated issues |
| `detect_antipatterns` | Queries Qdrant `engineering_antipatterns` for known bad patterns |
| `measure_complexity` | AST-based cyclomatic complexity calculation (Python) |
| `check_security` | OWASP Top 10 security audit via LLM analysis |

### MCP Test Server (port 8336)

Container: `omni-mcp-test`

| Tool | Description |
|------|-------------|
| `generate_tests` | LLM-based test suite generation for any framework |
| `suggest_test_cases` | Edge-case and boundary-condition identification |
| `analyze_coverage` | Parse JSON, LCOV, or Cobertura coverage reports |
| `generate_fixtures` | Create test fixtures and mock data from source code |

### MCP Deploy Server (port 8337)

Container: `omni-mcp-deploy`

| Tool | Description |
|------|-------------|
| `check_deploy_readiness` | Verify health checks, tests, and build status |
| `get_deploy_status` | Query Coolify for current deployment state |
| `rollback_deploy` | Initiate rollback to previous deployment version |
| `get_deploy_logs` | Retrieve deployment logs with level filtering |

### MCP Knowledge Server (port 8338)

Container: `omni-mcp-knowledge`

| Tool | Description |
|------|-------------|
| `search_knowledge` | Semantic search across Qdrant collections |
| `get_architecture_decisions` | Query ADR collection with status filtering |
| `find_similar_code` | Code similarity search via vector embeddings |
| `get_best_practices` | Domain-specific best-practice retrieval |

## API Endpoints

All four servers expose the same endpoint pattern:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness / readiness probe |
| `GET` | `/metrics` | Prometheus-compatible metrics |
| `GET` | `/api/v1/tools` | List available tools with schemas |
| `POST` | `/api/v1/tools/call` | Execute a tool by name |

### Tool Call Request

```json
{
  "tool_name": "analyze_code",
  "arguments": {
    "code": "def hello(): pass",
    "language": "python"
  }
}
```

### Tool Call Response

```json
{
  "tool_name": "analyze_code",
  "result": { "issues": [], "metrics": {}, "suggestions": [] },
  "error": null,
  "execution_time_ms": 1234.56
}
```

## Configuration

All servers share the same environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | per server | Service identifier |
| `SERVICE_PORT` | per server | HTTP listen port |
| `DATABASE_URL` | `postgresql+asyncpg://omni:omni@omni-postgres:5432/omni_mcp_servers` | PostgreSQL DSN |
| `REDIS_URL` | `redis://omni-redis:6379/12` | Redis connection URL |
| `QDRANT_URL` | `http://omni-qdrant:6333` | Qdrant vector database URL |
| `LITELLM_URL` | `http://omni-litellm:4000` | LiteLLM proxy URL |
| `COOLIFY_URL` | `http://omni-coolify:8000` | Coolify deployment platform URL |
| `MATTERMOST_WEBHOOK_URL` | `http://omni-mattermost:8065/hooks/mcp-servers` | Notification webhook |
| `LOG_LEVEL` | `INFO` | Logging level |

## Quick Start

```bash
# Copy environment config
cp .env.example .env

# Start all four servers
docker compose up -d

# Verify health
curl http://localhost:8335/health
curl http://localhost:8336/health
curl http://localhost:8337/health
curl http://localhost:8338/health

# List tools from the Analysis server
curl http://localhost:8335/api/v1/tools

# Call a tool
curl -X POST http://localhost:8335/api/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "measure_complexity", "arguments": {"code": "def f(x):\n  if x > 0:\n    return x\n  return -x"}}'
```

## Running Tests

```bash
pip install -r requirements.txt
pip install pytest pytest-anyio
pytest tests/ -v
```

## Project Structure

```
services/system-44-mcp-servers/
  docker-compose.yml       4 services (analysis, test, deploy, knowledge)
  Dockerfile               Multi-stage, non-root user
  requirements.txt         Pinned dependencies
  .env.example             Environment variable template
  src/
    __init__.py
    config.py              Shared Settings (pydantic-settings)
    models.py              Pydantic v2 data models
    routers/               Reserved for shared routers
      __init__.py
    services/              Reserved for shared services
      __init__.py
    utils/
      __init__.py
      notifications.py     Mattermost webhook helper
    mcp_servers/
      __init__.py
      analysis.py          MCP Analysis Server  (port 8335)
      test_server.py       MCP Test Server      (port 8336)
      deploy.py            MCP Deploy Server    (port 8337)
      knowledge.py         MCP Knowledge Server (port 8338)
  tests/
    __init__.py
    conftest.py            Shared fixtures (async clients)
    test_health.py         Health + metrics for all 4 servers
    test_analysis.py       Analysis tool listing + complexity tests
    test_knowledge.py      Knowledge tool definitions + schemas
```
