# New Service Documentation Template

## [Service Name]

**System Number**: [#]
**Container**: `omni-[name]`
**Port**: [port]
**Tier**: [Foundation | AI | Knowledge | Observability | Business | Infrastructure]
**Repository**: `http://omni-gitea:3000/omni-admin/[repo-name]`
**Owner**: [Team or individual]

---

## Purpose

[1-2 paragraph description of what this service does, why it exists, and what problem it solves within the Omni Quantum Elite platform.]

---

## Architecture

### Dependencies

| Service | Relationship | Required |
|---------|-------------|----------|
| [service-name] | [reads from / writes to / calls] | [Yes/No] |

### Data Flow

```
[Source] → [This Service] → [Destination]
```

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | [Python 3.12 / Go 1.22 / TypeScript 5.x] | |
| Framework | [FastAPI / Gin / Fastify] | |
| Database | [PostgreSQL / Neo4j / Redis / None] | |
| Messaging | [Redis pub/sub / Webhooks / None] | |

---

## Configuration

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SERVICE_NAME` | `[name]` | No | Service identifier |
| `LOG_LEVEL` | `info` | No | Logging level (debug, info, warn, error) |
| `PORT` | `[port]` | No | Listen port |
| `VAULT_ADDR` | `http://omni-vault:8200` | Yes | Vault address for secrets |
| `VAULT_TOKEN` | — | Yes | Vault authentication token |
| [add more] | | | |

### Secrets (in Vault)

Path: `secret/data/omni/[service-name]`

| Key | Description |
|-----|-------------|
| [key] | [description] |

---

## API Reference

### Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Liveness probe | None |
| GET | `/ready` | Readiness probe | None |
| GET | `/metrics` | Prometheus metrics | None |
| [METHOD] | [/path] | [description] | [Bearer / API Key / None] |

### Request/Response Examples

#### [Endpoint Name]

**Request**:
```bash
curl -X [METHOD] http://omni-[name]:[port]/[path] \
  -H "Content-Type: application/json" \
  -d '{
    "field": "value"
  }'
```

**Response** (200):
```json
{
  "field": "value"
}
```

**Error Response** (4xx/5xx):
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description"
  }
}
```

---

## Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `[service]_requests_total` | Counter | endpoint, status | Total requests |
| `[service]_request_duration_seconds` | Histogram | endpoint | Request latency |
| `[service]_errors_total` | Counter | endpoint, error_type | Error count |
| [add more] | | | |

### Grafana Dashboard

Dashboard ID: `[id]`
URL: `http://omni-grafana:3000/d/[id]`

---

## Deployment

### Docker Compose

```yaml
  omni-[name]:
    build:
      context: ./services/[name]
      dockerfile: Dockerfile
    container_name: omni-[name]
    restart: unless-stopped
    ports:
      - "[port]:[port]"
    environment:
      - SERVICE_NAME=[name]
      - LOG_LEVEL=info
    networks:
      - omni-quantum-network
    labels:
      omni.quantum.component: [name]
      omni.quantum.tier: [tier]
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:[port]/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### Build

```bash
docker compose build omni-[name]
docker compose up -d omni-[name]
```

### Logs

```bash
docker logs -f omni-[name]
```

---

## Operations

### Health Check

```bash
curl http://omni-[name]:[port]/health
curl http://omni-[name]:[port]/ready
```

### Scaling

[Describe if and how this service can be horizontally scaled.]

### Backup

[Describe what data needs backing up and how. Reference the backup-and-restore runbook.]

### Known Issues

| Issue | Workaround | Tracking |
|-------|------------|----------|
| [description] | [workaround] | [link to issue] |

---

## Runbooks

- [Deploy](/runbooks/deploy-new-service)
- [Incident Response](/runbooks/incident-response)
- [Backup and Restore](/runbooks/backup-and-restore)

---

## Changelog

| Date | Version | Change |
|------|---------|--------|
| YYYY-MM-DD | 1.0.0 | Initial release |

---

*Template version: 1.0 | Fill in all bracketed sections before publishing.*
