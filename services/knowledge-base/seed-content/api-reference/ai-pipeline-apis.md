# AI Pipeline APIs Reference

## Ollama — System 3

**Container**: `omni-ollama` | **Port**: 11434 | **Tier**: AI

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/generate` | Generate text completion |
| POST | `/api/chat` | Chat completion |
| POST | `/api/embeddings` | Generate embeddings |
| GET | `/api/tags` | List local models |
| POST | `/api/pull` | Pull a model from registry |
| POST | `/api/create` | Create a custom model |
| DELETE | `/api/delete` | Delete a model |
| POST | `/api/copy` | Copy a model |
| GET | `/api/show` | Show model info |
| GET | `/api/ps` | List running models |
| GET | `/` | Health check (returns "Ollama is running") |

### Example: Chat Completion
```bash
curl -X POST http://omni-ollama:11434/api/chat \
  -d '{
    "model": "codellama:13b",
    "messages": [{"role": "user", "content": "Write a Python singleton pattern"}],
    "stream": false
  }'
```

### Example: Generate Embeddings
```bash
curl -X POST http://omni-ollama:11434/api/embeddings \
  -d '{
    "model": "nomic-embed-text",
    "prompt": "Design pattern for data access layer"
  }'
```

### Available Models
| Model | Size | Use Case |
|-------|------|----------|
| codellama:13b | 7.4 GB | Code generation, completion |
| deepseek-coder:6.7b | 3.8 GB | Code generation, fast |
| starcoder2:7b | 4.0 GB | Code completion |
| nomic-embed-text | 274 MB | Text embeddings |
| llama3.1:8b | 4.7 GB | General text, reasoning |

---

## Vector Memory / Qdrant — System 15

**Container**: `omni-qdrant` | **Port**: 6333 (HTTP) / 6334 (gRPC) | **Tier**: Knowledge

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/collections` | List all collections |
| PUT | `/collections/{name}` | Create collection |
| GET | `/collections/{name}` | Get collection info |
| DELETE | `/collections/{name}` | Delete collection |
| PUT | `/collections/{name}/points` | Upsert points |
| POST | `/collections/{name}/points/search` | Search nearest neighbors |
| POST | `/collections/{name}/points/scroll` | Scroll/paginate points |
| POST | `/collections/{name}/points/delete` | Delete points |
| POST | `/collections/{name}/points/recommend` | Recommend similar points |
| PUT | `/collections/{name}/index` | Create payload index |
| GET | `/healthz` | Health check |
| GET | `/readyz` | Readiness check |

### Example: Create Collection
```bash
curl -X PUT http://omni-qdrant:6333/collections/code_embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    },
    "optimizers_config": {
      "memmap_threshold": 20000
    }
  }'
```

### Example: Search
```bash
curl -X POST http://omni-qdrant:6333/collections/code_embeddings/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, ...],
    "limit": 5,
    "filter": {
      "must": [{"key": "language", "match": {"value": "python"}}]
    },
    "with_payload": true
  }'
```

### Collections
| Collection | Vector Size | Use Case |
|-----------|-------------|----------|
| code_embeddings | 1536 | Code snippet embeddings |
| doc_embeddings | 1536 | Documentation embeddings |
| conversation_memory | 1536 | Chat/conversation history |
| pattern_cache | 1536 | Semantic cache for pattern lookups |

---

## Token Infinity — System 66

**Container**: `omni-token-infinity` | **Port**: 7600 | **Tier**: AI

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/context/build` | Build optimal context for an LLM prompt |
| POST | `/v1/context/search` | Search across all knowledge sources |
| GET | `/v1/context/sources` | List available knowledge sources |
| POST | `/v1/chat/completions` | RAG-augmented chat completion |
| GET | `/health` | Health check |
| GET | `/ready` | Readiness (checks Qdrant, Neo4j, Wiki.js) |
| GET | `/metrics` | Prometheus metrics |

### Example: Build Context
```bash
curl -X POST http://omni-token-infinity:7600/v1/context/build \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to implement circuit breaker pattern in Python",
    "max_tokens": 4000,
    "sources": ["qdrant", "neo4j", "wiki"],
    "language": "python"
  }'
```

### Example: RAG Chat
```bash
curl -X POST http://omni-token-infinity:7600/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Design a caching layer for our API"}],
    "rag_config": {
      "enabled": true,
      "sources": ["neo4j", "qdrant"],
      "max_context_tokens": 8000
    }
  }'
```

---

## AI Coder Alpha (OpenHands) — System 5

**Container**: `omni-openhands` | **Port**: 3100 | **Tier**: AI

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/tasks` | Create a new coding task |
| GET | `/api/v1/tasks/{id}` | Get task status and result |
| DELETE | `/api/v1/tasks/{id}` | Cancel a running task |
| GET | `/api/v1/tasks` | List recent tasks |
| WS | `/ws` | WebSocket for real-time task output |
| GET | `/health` | Health check |

### Example: Create Coding Task
```bash
curl -X POST http://omni-openhands:3100/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Add rate limiting middleware to the FastAPI application in /app/main.py",
    "workspace": "/workspace/project",
    "model": "gpt-4o"
  }'
```

---

## AI Coder Beta (SWE-Agent) — System 6

**Container**: `omni-swe-agent` | **Port**: 3200 | **Tier**: AI

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/solve` | Submit an issue for autonomous resolution |
| GET | `/api/v1/solve/{id}` | Get resolution status |
| GET | `/api/v1/solve/{id}/patch` | Get generated patch |
| GET | `/api/v1/history` | List past resolutions |
| GET | `/health` | Health check |

### Example: Submit Issue
```bash
curl -X POST http://omni-swe-agent:3200/api/v1/solve \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "http://omni-gitea:3000/omni-admin/my-project.git",
    "issue_description": "Fix the N+1 query problem in the user listing endpoint",
    "model": "gpt-4o"
  }'
```

---

## Build Forge (Coder) — System 7

**Container**: `omni-coder` | **Port**: 7080 | **Tier**: Development

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/workspaces` | List workspaces |
| POST | `/api/v2/workspaces` | Create workspace |
| GET | `/api/v2/workspaces/{id}` | Get workspace details |
| PUT | `/api/v2/workspaces/{id}/builds` | Start/stop workspace |
| GET | `/api/v2/templates` | List templates |
| POST | `/api/v2/templates` | Create template |
| GET | `/api/v2/users/me` | Current user info |
| GET | `/api/v2/buildinfo` | Build/version info |

### Authentication
Session token via `Coder-Session-Token` header.

### Example: Create Workspace
```bash
curl -X POST http://omni-coder:7080/api/v2/workspaces \
  -H "Coder-Session-Token: ${CODER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "debug-session",
    "template_id": "python-dev",
    "rich_parameter_values": []
  }'
```

---

## Code Forge (Woodpecker CI) — System 8

**Container**: `omni-woodpecker` | **Port**: 8000 | **Tier**: CI/CD

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/repos` | List repositories |
| GET | `/api/repos/{owner}/{name}` | Get repository |
| POST | `/api/repos/{owner}/{name}` | Activate repository |
| GET | `/api/repos/{owner}/{name}/pipelines` | List pipelines |
| POST | `/api/repos/{owner}/{name}/pipelines` | Trigger pipeline |
| GET | `/api/repos/{owner}/{name}/pipelines/{number}` | Get pipeline details |
| GET | `/api/repos/{owner}/{name}/pipelines/{number}/logs/{step}` | Get step logs |
| GET | `/api/user` | Current user |

### Authentication
Personal token via `Authorization: Bearer {token}` header.

### Example: Trigger Pipeline
```bash
curl -X POST http://omni-woodpecker:8000/api/repos/omni-admin/my-project/pipelines \
  -H "Authorization: Bearer ${WOODPECKER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"branch": "main"}'
```

---

*Last updated: 2025-01-01 | All endpoints use JSON unless otherwise noted.*
