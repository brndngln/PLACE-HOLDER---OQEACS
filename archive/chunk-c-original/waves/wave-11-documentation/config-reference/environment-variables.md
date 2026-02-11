# Environment Variables Reference
## Omni Quantum Elite v3.0

---

## Core Services

### Master Orchestrator (omni-orchestrator:9500)
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `9500` | Service port |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://omni-redis:6379` | Redis connection |
| `LITELLM_URL` | `http://omni-litellm:4000` | LiteLLM gateway |
| `QDRANT_URL` | `http://omni-qdrant:6333` | Vector database |
| `MATTERMOST_WEBHOOK_URL` | - | Notification webhook |
| `LOG_LEVEL` | `INFO` | Logging level |

### LiteLLM Gateway (omni-litellm:4000)
| Variable | Default | Description |
|----------|---------|-------------|
| `LITELLM_MASTER_KEY` | - | Master API key |
| `OLLAMA_API_BASE` | `http://omni-ollama:11434` | Ollama endpoint |
| `DATABASE_URL` | `postgresql://...` | For spend tracking |
| `REDIS_URL` | `redis://omni-redis:6379` | For caching |

### Token Infinity (omni-token-infinity:9600)
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `9600` | Service port |
| `PROVIDER_CONFIG_PATH` | `/config/providers.yaml` | Provider configuration |
| `HEALTH_CHECK_INTERVAL` | `60` | Health check interval (seconds) |
| `FAILOVER_THRESHOLD` | `3` | Failures before failover |

### Semantic Cache (omni-semantic-cache:8380)
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8380` | Service port |
| `QDRANT_URL` | `http://omni-qdrant:6333` | Vector database |
| `SIMILARITY_THRESHOLD` | `0.95` | Cache hit threshold |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL |

---

## Data Stores

### PostgreSQL (omni-postgres:5432)
| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `fortress` | Database user |
| `POSTGRES_PASSWORD` | - | Database password |
| `POSTGRES_DB` | `financial_fortress` | Default database |

### Redis (omni-redis:6379)
| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_PASSWORD` | - | Optional password |
| `REDIS_MAXMEMORY` | `256mb` | Memory limit |
| `REDIS_MAXMEMORY_POLICY` | `allkeys-lru` | Eviction policy |

### Qdrant (omni-qdrant:6333)
| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT__SERVICE__GRPC_PORT` | `6334` | gRPC port |
| `QDRANT__LOG_LEVEL` | `INFO` | Log level |

### MinIO (omni-minio:9000)
| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ROOT_USER` | `minioadmin` | Admin username |
| `MINIO_ROOT_PASSWORD` | - | Admin password |

---

## Security

### Vault (omni-vault:8200)
| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_DEV_ROOT_TOKEN_ID` | - | Dev mode token |
| `VAULT_ADDR` | `http://127.0.0.1:8200` | Vault address |

### Authentik (omni-authentik:9000)
| Variable | Default | Description |
|----------|---------|-------------|
| `AUTHENTIK_SECRET_KEY` | - | Secret key |
| `AUTHENTIK_BOOTSTRAP_PASSWORD` | - | Admin password |
| `AUTHENTIK_BOOTSTRAP_EMAIL` | - | Admin email |

---

## Deployment

### Blue-Green (omni-blue-green:9650)
| Variable | Default | Description |
|----------|---------|-------------|
| `HEALTH_CHECK_TIMEOUT` | `60` | Health check timeout (seconds) |
| `HEALTH_CHECK_INTERVAL` | `5` | Check interval (seconds) |

### Canary (omni-canary:9651)
| Variable | Default | Description |
|----------|---------|-------------|
| `ERROR_RATE_THRESHOLD` | `0.05` | Rollback threshold (5%) |
| `LATENCY_P99_THRESHOLD_MS` | `500` | Latency threshold |

---

## Observability

### Prometheus (omni-prometheus:9090)
| Variable | Default | Description |
|----------|---------|-------------|
| `--storage.tsdb.retention.time` | `15d` | Data retention |

### Grafana (omni-grafana:3000)
| Variable | Default | Description |
|----------|---------|-------------|
| `GF_SECURITY_ADMIN_PASSWORD` | - | Admin password |
| `GF_AUTH_ANONYMOUS_ENABLED` | `false` | Anonymous access |

---

*Generated: 2024-01-01*
