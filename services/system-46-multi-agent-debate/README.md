# System 46 — Multi-Agent Debate Engine

Orchestrates multi-agent debates for coding tasks. Specialized AI agents
(Architect, Implementer, Reviewer, Security, Performance, Devil's Advocate)
argue about the best approach **before** any code is written.

## Architecture

```
Task → [Proposal Phase] → [Critique Phase] → [Rebuttal Phase]
                                                      ↓
     [Final Code] ← [Synthesis Phase] ← [Voting Phase]
```

## Agent Roles

| Agent | Expertise | Weight |
|-------|-----------|--------|
| **Architect** | System design, patterns, scalability | 1.5 |
| **Implementer** | Algorithms, error handling, idiomatic code | 1.3 |
| **Reviewer** | Code quality, readability, maintainability | 1.2 |
| **Security** | OWASP, auth, input validation, threat modeling | 1.4 |
| **Performance** | Profiling, caching, complexity, concurrency | 1.1 |
| **Devil's Advocate** | Edge cases, failure modes, chaos testing | 1.0 |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/debate` | Start a full multi-agent debate |
| `GET`  | `/api/v1/debate/{id}` | Retrieve debate result |
| `GET`  | `/api/v1/debates` | List all debates |
| `POST` | `/api/v1/review` | Quick multi-perspective code review |
| `GET`  | `/health` | Health check |
| `GET`  | `/metrics` | Prometheus metrics |

## Quick Start

```bash
cp .env.example .env
docker compose up -d
curl http://localhost:9650/health

# Start a debate
curl -X POST http://localhost:9650/api/v1/debate \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Implement a rate limiter using token bucket algorithm",
    "language": "python",
    "agents": ["architect", "implementer", "reviewer", "security", "performance"]
  }'
```

## Running Tests

```bash
pip install -r requirements.txt
pip install pytest pytest-anyio
pytest tests/ -v
```
