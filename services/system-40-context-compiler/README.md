# System 40: Context Compiler

Assembles the optimal set of tokens for each LLM invocation. Instead of dumping everything into the prompt, this service intelligently selects, ranks, and budgets context based on the specific task.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/compile | Compile context for a task |
| GET | /api/v1/templates | List context templates |
| GET | /api/v1/templates/{id} | Get specific template |
| POST | /api/v1/effectiveness | Report context effectiveness score |
| GET | /api/v1/stats | Context compilation statistics |
| GET | /health | Health check |
| GET | /metrics | Prometheus metrics |

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| SERVICE_PORT | 8325 | Service port |
| DATABASE_URL | postgresql://omni:omni@omni-postgres:5432/omni_quantum | PostgreSQL connection |
| REDIS_URL | redis://omni-redis:6379/0 | Redis connection |
| QDRANT_URL | http://omni-qdrant:6333 | Qdrant connection |
| LITELLM_URL | http://omni-litellm:4000 | LiteLLM proxy |
| DEFAULT_TOKEN_BUDGET | 128000 | Default token budget |
| EMBEDDING_MODEL | text-embedding-3-small | Embedding model |
| COMPRESSION_MODEL | qwen2.5-72b | Model for context compression |

## Integration

- **Qdrant**: Semantic search across knowledge_base and engineering_antipatterns collections
- **LiteLLM**: Embeddings and context compression
- **Rules Engine (GI-5)**: Architecture rules at omni-rules:9624
- **Redis**: Caching and feedback storage
- **PostgreSQL**: Effectiveness tracking
