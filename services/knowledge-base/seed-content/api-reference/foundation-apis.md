# Foundation APIs Reference

## Backup Fortress (Duplicati) — System 1

**Container**: `omni-duplicati` | **Port**: 8200 | **Tier**: Foundation

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/serverstate` | Server state and running operations |
| GET | `/api/v1/backups` | List all backup configurations |
| GET | `/api/v1/backup/{id}` | Get backup configuration by ID |
| POST | `/api/v1/backup/{id}/run` | Trigger a backup run |
| POST | `/api/v1/backup/{id}/restore` | Restore from a backup |
| GET | `/api/v1/backup/{id}/files/{path}` | Browse backup file tree |
| DELETE | `/api/v1/backup/{id}` | Delete a backup configuration |
| GET | `/api/v1/systeminfo` | System information and version |
| POST | `/api/v1/backup` | Create a new backup configuration |

### Authentication
API key via `X-API-KEY` header. Generated in Duplicati web UI under Settings → API Key.

### Example: Trigger Backup
```bash
curl -X POST http://omni-duplicati:8200/api/v1/backup/1/run \
  -H "X-API-KEY: ${DUPLICATI_API_KEY}"
```

### Example: List Backups
```bash
curl http://omni-duplicati:8200/api/v1/backups \
  -H "X-API-KEY: ${DUPLICATI_API_KEY}"
```

---

## Security Nexus (Vault) — System 2

**Container**: `omni-vault` | **Port**: 8200 | **Tier**: Foundation

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/sys/health` | Vault health status |
| GET | `/v1/sys/seal-status` | Seal/unseal status |
| POST | `/v1/sys/unseal` | Unseal Vault |
| GET | `/v1/secret/data/{path}` | Read KV v2 secret |
| POST | `/v1/secret/data/{path}` | Create/update KV v2 secret |
| DELETE | `/v1/secret/data/{path}` | Soft-delete secret |
| POST | `/v1/auth/token/create` | Create a new token |
| GET | `/v1/auth/token/lookup-self` | Look up current token |
| POST | `/v1/auth/approle/login` | AppRole authentication |
| GET | `/v1/sys/mounts` | List secret engines |

### Authentication
Token via `X-Vault-Token` header or AppRole via `/v1/auth/approle/login`.

### Example: Read Secret
```bash
curl http://omni-vault:8200/v1/secret/data/omni/litellm \
  -H "X-Vault-Token: ${VAULT_TOKEN}"
```

### Example: Write Secret
```bash
curl -X POST http://omni-vault:8200/v1/secret/data/omni/new-service \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -d '{"data": {"api_key": "sk-xxx", "db_password": "yyy"}}'
```

---

## LiteLLM Proxy — System 4

**Container**: `omni-litellm` | **Port**: 4000 | **Tier**: AI

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat/completions` | OpenAI-compatible chat completion |
| POST | `/v1/completions` | OpenAI-compatible text completion |
| POST | `/v1/embeddings` | Generate embeddings |
| GET | `/v1/models` | List available models |
| GET | `/v1/model/info` | Model configuration info |
| GET | `/health` | Health check |
| GET | `/health/readiness` | Readiness check |
| POST | `/key/generate` | Generate API key |
| GET | `/key/info` | API key information |
| GET | `/spend/logs` | Token spend logs |
| GET | `/global/spend` | Global spend summary |

### Authentication
Bearer token via `Authorization: Bearer sk-xxx` header.

### Example: Chat Completion
```bash
curl -X POST http://omni-litellm:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Explain the repository pattern"}],
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

### Example: Generate Embeddings
```bash
curl -X POST http://omni-litellm:4000/v1/embeddings \
  -H "Authorization: Bearer ${LITELLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-3-small",
    "input": "Design pattern for data access layer"
  }'
```

### Model Routing
LiteLLM routes requests to the appropriate backend based on model name:
- `gpt-*` → OpenAI API
- `claude-*` → Anthropic API
- `ollama/*` → Local Ollama instance (omni-ollama:11434)
- `deepseek-*` → DeepSeek API

---

## Prometheus — Metrics Collection

**Container**: `omni-prometheus` | **Port**: 9090 | **Tier**: Foundation

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/query` | Instant PromQL query |
| GET | `/api/v1/query_range` | Range PromQL query |
| GET | `/api/v1/series` | Find matching time series |
| GET | `/api/v1/labels` | List label names |
| GET | `/api/v1/label/{name}/values` | Label values |
| GET | `/api/v1/targets` | Scrape targets status |
| GET | `/-/healthy` | Health check |
| GET | `/-/ready` | Readiness check |

### Example: Query Metric
```bash
curl 'http://omni-prometheus:9090/api/v1/query?query=pattern_queries_total'
```

---

## Source Control (Gitea) — System 22

**Container**: `omni-gitea` | **Port**: 3000 | **Tier**: Foundation

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/repos/search` | Search repositories |
| GET | `/api/v1/repos/{owner}/{repo}` | Get repository details |
| POST | `/api/v1/orgs/{org}/repos` | Create repository |
| GET | `/api/v1/repos/{owner}/{repo}/commits` | List commits |
| GET | `/api/v1/repos/{owner}/{repo}/branches` | List branches |
| POST | `/api/v1/repos/{owner}/{repo}/hooks` | Create webhook |
| GET | `/api/v1/user` | Get authenticated user |
| POST | `/api/v1/repos/{owner}/{repo}/contents/{filepath}` | Create/update file |

### Authentication
Token via `Authorization: token {access_token}` header.

### Example: List Repos
```bash
curl http://omni-gitea:3000/api/v1/repos/search \
  -H "Authorization: token ${GITEA_TOKEN}"
```

---

## Object Store (MinIO) — System 21

**Container**: `omni-minio` | **Port**: 9000 (API) / 9001 (Console) | **Tier**: Foundation

### Endpoints (S3-compatible)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List buckets |
| PUT | `/{bucket}` | Create bucket |
| GET | `/{bucket}` | List objects in bucket |
| PUT | `/{bucket}/{key}` | Upload object |
| GET | `/{bucket}/{key}` | Download object |
| DELETE | `/{bucket}/{key}` | Delete object |
| HEAD | `/{bucket}/{key}` | Object metadata |

### Authentication
AWS Signature V4 with access key and secret key. Use any S3-compatible SDK.

### Example: Upload (mc CLI)
```bash
mc alias set omni http://omni-minio:9000 ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY}
mc cp backup.tar.gz omni/backups/
```

---

## Gateway Sentinel (Traefik) — System 14

**Container**: `omni-traefik` | **Port**: 80/443 (proxy), 8080 (dashboard) | **Tier**: Infrastructure

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/overview` | Dashboard overview |
| GET | `/api/http/routers` | List HTTP routers |
| GET | `/api/http/services` | List HTTP services |
| GET | `/api/http/middlewares` | List HTTP middlewares |
| GET | `/api/entrypoints` | List entrypoints |
| GET | `/api/rawdata` | Full configuration dump |
| GET | `/ping` | Health check |

### Example: List Services
```bash
curl http://omni-traefik:8080/api/http/services
```

### Routing Labels
Services register routes via Docker labels:
```yaml
labels:
  - "traefik.http.routers.myservice.rule=Host(`myservice.omni.local`)"
  - "traefik.http.services.myservice.loadbalancer.server.port=8080"
```

---

*Last updated: 2025-01-01 | API versions may vary — check service health endpoints for current versions.*
