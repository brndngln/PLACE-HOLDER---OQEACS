# Runbook: Secret Rotation

## Overview
Procedures for rotating secrets, API keys, tokens, and credentials across all Omni Quantum Elite services.

**Audience**: Security engineers, platform engineers
**Estimated time**: 30–60 minutes
**Risk level**: High
**Schedule**: Monthly (recommended) or immediately after suspected compromise

---

## Secret Inventory

| Secret | Stored In | Used By | Rotation Method |
|--------|-----------|---------|-----------------|
| PostgreSQL root password | Vault `secret/omni/postgres` | All DB-dependent services | Update Vault + restart services |
| Neo4j password | Vault `secret/omni/neo4j` | GraphRAG API, init scripts | Update Vault + Neo4j + restart |
| Redis password | Vault `secret/omni/redis` | Semantic Cache, services | Update Vault + Redis + restart |
| LiteLLM master key | Vault `secret/omni/litellm` | LiteLLM Proxy | Update Vault + restart LiteLLM |
| OpenAI API key | Vault `secret/omni/openai` | LiteLLM Proxy | Update Vault + restart LiteLLM |
| Anthropic API key | Vault `secret/omni/anthropic` | LiteLLM Proxy | Update Vault + restart LiteLLM |
| Gitea admin token | Vault `secret/omni/gitea` | Knowledge Ingestor, Wiki.js | Regenerate in Gitea UI + update Vault |
| Authentik client secrets | Vault `secret/omni/authentik` | Wiki.js, Grafana, Portainer | Regenerate in Authentik + update Vault |
| MinIO access/secret keys | Vault `secret/omni/minio` | Duplicati, all backup scripts | Update Vault + MinIO + restart |
| Vault root token | Vault init output (sealed) | Platform admin | Rekey Vault |
| Woodpecker tokens | Vault `secret/omni/woodpecker` | CI/CD pipelines | Regenerate in Woodpecker UI |
| Orchestrator token | Vault `secret/omni/orchestrator` | All services via orchestrator | Update Vault + restart orchestrator |

---

## General Rotation Procedure

### Step 1 — Generate New Secret

```bash
# Generate a cryptographically secure random string
NEW_SECRET=$(openssl rand -base64 32 | tr -d '=/+' | head -c 40)
echo "New secret generated (do not log in production)"
```

### Step 2 — Update Vault

```bash
# Read current secret (to preserve other fields)
CURRENT=$(curl -sf http://omni-vault:8200/v1/secret/data/omni/<service> \
  -H "X-Vault-Token: ${VAULT_TOKEN}" | jq '.data.data')

# Update with new secret
curl -X POST http://omni-vault:8200/v1/secret/data/omni/<service> \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"data\": $(echo ${CURRENT} | jq '.password = \"'${NEW_SECRET}'\"')}"
```

### Step 3 — Update the Service

Apply the new secret to the service (method varies — see specific procedures below).

### Step 4 — Verify

```bash
# Check service health after rotation
curl -sf http://omni-<service>:<port>/health
curl -sf http://omni-<service>:<port>/ready
```

### Step 5 — Invalidate Old Secret

Ensure the old secret no longer works (test with old credentials should fail).

---

## Specific Rotation Procedures

### PostgreSQL Password Rotation

```bash
# 1. Generate new password
NEW_PG_PASS=$(openssl rand -base64 32 | tr -d '=/+' | head -c 40)

# 2. Update PostgreSQL
docker exec omni-postgres psql -U postgres -c "ALTER USER postgres PASSWORD '${NEW_PG_PASS}'"

# 3. Update Vault
curl -X POST http://omni-vault:8200/v1/secret/data/omni/postgres \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -d "{\"data\": {\"password\": \"${NEW_PG_PASS}\", \"username\": \"postgres\"}}"

# 4. Restart dependent services (they read password from Vault on startup)
docker compose restart omni-wikijs omni-langfuse omni-accounts omni-invoicing omni-analytics omni-crm

# 5. Verify
docker exec omni-postgres psql -U postgres -c "SELECT 1"
```

### Neo4j Password Rotation

```bash
# 1. Generate new password
NEW_NEO4J_PASS=$(openssl rand -base64 32 | tr -d '=/+' | head -c 40)

# 2. Update Neo4j
docker exec omni-neo4j cypher-shell -u neo4j -p "${OLD_NEO4J_PASS}" \
  "ALTER CURRENT USER SET PASSWORD FROM '${OLD_NEO4J_PASS}' TO '${NEW_NEO4J_PASS}'"

# 3. Update Vault
curl -X POST http://omni-vault:8200/v1/secret/data/omni/neo4j \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -d "{\"data\": {\"password\": \"${NEW_NEO4J_PASS}\", \"username\": \"neo4j\"}}"

# 4. Restart GraphRAG API
docker compose restart omni-neo4j-graphrag-api

# 5. Verify
curl -sf http://omni-neo4j-graphrag-api:7475/ready
```

### LiteLLM API Keys Rotation

```bash
# 1. Get new API keys from provider dashboards (OpenAI, Anthropic, etc.)

# 2. Update Vault
curl -X POST http://omni-vault:8200/v1/secret/data/omni/litellm \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -d '{
    "data": {
      "openai_api_key": "sk-new-openai-key",
      "anthropic_api_key": "sk-ant-new-anthropic-key",
      "master_key": "sk-new-litellm-master-key"
    }
  }'

# 3. Restart LiteLLM
docker compose restart omni-litellm

# 4. Verify
curl http://omni-litellm:4000/v1/models -H "Authorization: Bearer sk-new-litellm-master-key"
```

### Gitea Token Rotation

```bash
# 1. Generate new token in Gitea UI:
#    Settings → Applications → Generate New Token

# 2. Update Vault
curl -X POST http://omni-vault:8200/v1/secret/data/omni/gitea \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -d "{\"data\": {\"admin_token\": \"${NEW_GITEA_TOKEN}\"}}"

# 3. Restart services using Gitea token
docker compose restart omni-knowledge-ingestor omni-wikijs

# 4. Delete old token in Gitea UI

# 5. Verify
curl http://omni-gitea:3000/api/v1/user -H "Authorization: token ${NEW_GITEA_TOKEN}"
```

### Authentik OIDC Client Secret Rotation

```bash
# 1. In Authentik admin panel:
#    Applications → Providers → Select provider → Regenerate client secret

# 2. Update Vault
curl -X POST http://omni-vault:8200/v1/secret/data/omni/authentik \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -d "{\"data\": {\"wikijs_client_secret\": \"${NEW_SECRET}\"}}"

# 3. Restart affected services
docker compose restart omni-wikijs

# 4. Verify SSO login still works
```

### Vault Root Token Rotation (Rekey)

> **CRITICAL**: This procedure requires multiple unseal key holders. Schedule in advance.

```bash
# 1. Initialize rekey
curl -X POST http://omni-vault:8200/v1/sys/rekey/init \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -d '{"secret_shares": 5, "secret_threshold": 3}'

# 2. Submit unseal keys (repeat for threshold number of keys)
curl -X POST http://omni-vault:8200/v1/sys/rekey/update \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  -d '{"key": "<unseal_key>", "nonce": "<nonce_from_init>"}'

# 3. Store new unseal keys securely (offline, separate locations)

# 4. Generate new root token
curl -X POST http://omni-vault:8200/v1/sys/generate-root/attempt \
  -H "X-Vault-Token: ${VAULT_TOKEN}"
```

---

## Automated Rotation Script

```bash
#!/usr/bin/env bash
# rotate-secrets.sh — Rotate all service secrets
set -euo pipefail

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [secret-rotation] $*"; }

VAULT_ADDR="http://omni-vault:8200"
VAULT_TOKEN="${VAULT_TOKEN:?VAULT_TOKEN required}"

rotate_service_secret() {
    local service="$1"
    local field="$2"
    local new_secret
    new_secret=$(openssl rand -base64 32 | tr -d '=/+' | head -c 40)

    log "Rotating ${field} for ${service}..."

    # Read current
    local current
    current=$(curl -sf "${VAULT_ADDR}/v1/secret/data/omni/${service}" \
        -H "X-Vault-Token: ${VAULT_TOKEN}" | jq -r ".data.data")

    # Update
    local updated
    updated=$(echo "${current}" | jq --arg f "${field}" --arg v "${new_secret}" '.[$f] = $v')

    curl -sf -X POST "${VAULT_ADDR}/v1/secret/data/omni/${service}" \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        -d "{\"data\": ${updated}}" > /dev/null

    log "Vault updated for ${service}.${field}"
    echo "${new_secret}"
}

log "Starting secret rotation..."

# Rotate database passwords
rotate_service_secret "postgres" "password"
rotate_service_secret "neo4j" "password"
rotate_service_secret "redis" "password"

# Restart all services
log "Restarting services..."
docker compose restart

log "Secret rotation complete. Verify all services are healthy."
```

---

## Emergency Rotation (Suspected Compromise)

1. **Immediately** rotate all secrets listed above
2. **Revoke** all active Vault tokens: `vault token revoke -mode=orphan <token>`
3. **Invalidate** all LiteLLM API keys and generate new ones
4. **Rotate** Gitea tokens and Authentik secrets
5. **Audit** Vault access logs: `curl http://omni-vault:8200/v1/sys/audit-hash/file`
6. **Review** Langfuse traces for unauthorized LLM API usage
7. **Create** incident report per [Incident Response](/runbooks/incident-response)

---

## Verification Checklist

After rotation:
- [ ] All services report `healthy` via `/health`
- [ ] All services report `ready` via `/ready`
- [ ] Old credentials fail authentication
- [ ] New credentials work correctly
- [ ] Vault audit log shows the rotation
- [ ] No error spikes in Grafana dashboards
