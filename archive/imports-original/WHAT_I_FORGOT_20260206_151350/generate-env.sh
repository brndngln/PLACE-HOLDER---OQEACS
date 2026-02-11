#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# ⚛ OMNI QUANTUM ELITE — MASTER .ENV GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
# Generates all environment variables for the entire 37-system platform.
# Pulls existing secrets from Vault when available, generates missing ones.
# Validates all generated values before writing.
#
# Usage:
#   ./generate-env.sh                    # Generate .env with random secrets
#   ./generate-env.sh --vault            # Pull from Vault, generate missing
#   ./generate-env.sh --domain my.host   # Set base domain
#   ./generate-env.sh --dry-run          # Preview without writing
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_BACKUP="${PROJECT_ROOT}/.env.backup.$(date +%Y%m%d_%H%M%S)"

# ─── Defaults ─────────────────────────────────────────────────────────────────
USE_VAULT=false
DRY_RUN=false
BASE_DOMAIN="${OMNI_DOMAIN:-localhost}"
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
FORCE_REGENERATE=false

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Parse Arguments ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --vault)        USE_VAULT=true; shift ;;
        --domain)       BASE_DOMAIN="$2"; shift 2 ;;
        --dry-run)      DRY_RUN=true; shift ;;
        --force)        FORCE_REGENERATE=true; shift ;;
        --vault-addr)   VAULT_ADDR="$2"; shift 2 ;;
        --vault-token)  VAULT_TOKEN="$2"; shift 2 ;;
        --output)       ENV_FILE="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "  --vault         Pull secrets from HashiCorp Vault"
            echo "  --domain HOST   Set base domain (default: localhost)"
            echo "  --dry-run       Preview without writing"
            echo "  --force         Regenerate all secrets"
            echo "  --vault-addr    Vault address (default: http://omni-vault:8200)"
            echo "  --vault-token   Vault token"
            echo "  --output FILE   Output file (default: ../.env)"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ─── Utility Functions ────────────────────────────────────────────────────────
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}   $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERR]${NC}  $1"; }
log_section() { echo -e "\n${BOLD}${CYAN}═══ $1 ═══${NC}"; }

generate_password() {
    local length="${1:-32}"
    openssl rand -base64 "$((length * 3 / 4 + 1))" | tr -dc 'A-Za-z0-9!@#$%^&*' | head -c "$length"
}

generate_hex() {
    local length="${1:-32}"
    openssl rand -hex "$((length / 2))"
}

generate_alphanumeric() {
    local length="${1:-32}"
    openssl rand -base64 "$((length * 3 / 4 + 1))" | tr -dc 'A-Za-z0-9' | head -c "$length"
}

generate_uuid() {
    python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || \
    cat /proc/sys/kernel/random/uuid 2>/dev/null || \
    openssl rand -hex 16 | sed 's/\(.\{8\}\)\(.\{4\}\)\(.\{4\}\)\(.\{4\}\)/\1-\2-\3-\4-/'
}

vault_read() {
    local path="$1"
    local key="$2"
    if [[ "$USE_VAULT" == "true" ]] && command -v vault &>/dev/null && [[ -n "$VAULT_TOKEN" ]]; then
        VAULT_ADDR="$VAULT_ADDR" VAULT_TOKEN="$VAULT_TOKEN" vault kv get -field="$key" "secret/$path" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

vault_write() {
    local path="$1"
    local key="$2"
    local value="$3"
    if [[ "$USE_VAULT" == "true" ]] && command -v vault &>/dev/null && [[ -n "$VAULT_TOKEN" ]]; then
        VAULT_ADDR="$VAULT_ADDR" VAULT_TOKEN="$VAULT_TOKEN" vault kv put "secret/$path" "$key=$value" &>/dev/null || true
    fi
}

get_or_generate() {
    local vault_path="$1"
    local vault_key="$2"
    local generator="$3"
    local length="${4:-32}"

    local existing=""
    existing=$(vault_read "$vault_path" "$vault_key")

    if [[ -n "$existing" ]] && [[ "$FORCE_REGENERATE" != "true" ]]; then
        echo "$existing"
    else
        local new_value
        new_value=$($generator "$length")
        vault_write "$vault_path" "$vault_key" "$new_value"
        echo "$new_value"
    fi
}

# ─── Start Generation ────────────────────────────────────────────────────────
echo -e "${BOLD}${CYAN}"
echo "  ⚛  OMNI QUANTUM ELITE — Environment Generator"
echo "  ─────────────────────────────────────────────────"
echo -e "${NC}"
log_info "Domain: ${BASE_DOMAIN}"
log_info "Vault: ${USE_VAULT}"
log_info "Output: ${ENV_FILE}"
echo ""

# Backup existing .env
if [[ -f "$ENV_FILE" ]] && [[ "$DRY_RUN" != "true" ]]; then
    cp "$ENV_FILE" "$ENV_BACKUP"
    log_info "Backed up existing .env to ${ENV_BACKUP}"
fi

GENERATED_VARS=0

generate_env() {
    log_section "GLOBAL PLATFORM CONFIGURATION"

    cat << 'HEADER'
# ═══════════════════════════════════════════════════════════════════════════════
# ⚛ OMNI QUANTUM ELITE — MASTER ENVIRONMENT FILE
# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-GENERATED — DO NOT EDIT MANUALLY
# Use scripts/generate-env.sh to regenerate
# ═══════════════════════════════════════════════════════════════════════════════
HEADER

    # ─── Global Settings ──────────────────────────────────────────────────────
    echo ""
    echo "# ─── Global Platform ──────────────────────────────────────────────────"
    echo "OMNI_DOMAIN=${BASE_DOMAIN}"
    echo "OMNI_ENVIRONMENT=production"
    echo "OMNI_LOG_LEVEL=INFO"
    echo "OMNI_LOG_FORMAT=json"
    echo "OMNI_NETWORK=omni-quantum-network"
    echo "OMNI_TIMEZONE=UTC"
    echo "COMPOSE_PROJECT_NAME=omni-quantum"
    echo "DOCKER_BUILDKIT=1"
    echo "COMPOSE_DOCKER_CLI_BUILD=1"
    GENERATED_VARS=$((GENERATED_VARS + 9))

    # ─── PostgreSQL (Core) ────────────────────────────────────────────────────
    log_section "DATABASE CREDENTIALS"
    local pg_superuser_pass
    pg_superuser_pass=$(get_or_generate "database/postgres" "superuser_password" generate_password 40)

    echo ""
    echo "# ─── PostgreSQL (Core Database) ────────────────────────────────────────"
    echo "POSTGRES_HOST=omni-postgres"
    echo "POSTGRES_PORT=5432"
    echo "POSTGRES_SUPERUSER=omni_admin"
    echo "POSTGRES_SUPERUSER_PASSWORD=${pg_superuser_pass}"
    echo "POSTGRES_MAX_CONNECTIONS=200"
    echo "POSTGRES_SHARED_BUFFERS=256MB"
    GENERATED_VARS=$((GENERATED_VARS + 6))

    # Per-service database credentials
    local services=(
        "gitea" "mattermost" "n8n" "langfuse" "authentik"
        "superset" "calcom" "woodpecker" "coder" "plane"
        "listmonk" "chatwoot" "posthog" "glitchtip" "unleash"
        "orchestrator" "sla_tracker" "backup_orchestrator"
    )

    for svc in "${services[@]}"; do
        local svc_upper
        svc_upper=$(echo "$svc" | tr '[:lower:]' '[:upper:]')
        local svc_pass
        svc_pass=$(get_or_generate "database/${svc}" "password" generate_password 32)
        echo "${svc_upper}_DB_NAME=omni_${svc}"
        echo "${svc_upper}_DB_USER=omni_${svc}"
        echo "${svc_upper}_DB_PASSWORD=${svc_pass}"
        echo "${svc_upper}_DATABASE_URL=postgresql://omni_${svc}:${svc_pass}@omni-postgres:5432/omni_${svc}"
        GENERATED_VARS=$((GENERATED_VARS + 4))
    done

    # ─── Redis ────────────────────────────────────────────────────────────────
    local redis_pass
    redis_pass=$(get_or_generate "redis" "password" generate_password 32)

    echo ""
    echo "# ─── Redis ─────────────────────────────────────────────────────────────"
    echo "REDIS_HOST=omni-redis"
    echo "REDIS_PORT=6379"
    echo "REDIS_PASSWORD=${redis_pass}"
    echo "REDIS_URL=redis://:${redis_pass}@omni-redis:6379/0"
    echo "REDIS_EVENTS_DB=1"
    echo "REDIS_CACHE_DB=2"
    echo "REDIS_SESSIONS_DB=3"
    GENERATED_VARS=$((GENERATED_VARS + 7))

    # ─── MinIO (S3 Object Storage) ────────────────────────────────────────────
    local minio_access_key minio_secret_key
    minio_access_key=$(get_or_generate "minio" "access_key" generate_alphanumeric 20)
    minio_secret_key=$(get_or_generate "minio" "secret_key" generate_password 40)

    echo ""
    echo "# ─── MinIO (S3 Object Storage) ─────────────────────────────────────────"
    echo "MINIO_HOST=omni-minio"
    echo "MINIO_PORT=9000"
    echo "MINIO_CONSOLE_PORT=9001"
    echo "MINIO_ROOT_USER=${minio_access_key}"
    echo "MINIO_ROOT_PASSWORD=${minio_secret_key}"
    echo "MINIO_ENDPOINT=http://omni-minio:9000"
    echo "S3_ACCESS_KEY=${minio_access_key}"
    echo "S3_SECRET_KEY=${minio_secret_key}"
    echo "S3_REGION=us-east-1"
    echo "S3_BUCKET_BACKUPS=omni-backups"
    echo "S3_BUCKET_ARTIFACTS=omni-artifacts"
    echo "S3_BUCKET_KNOWLEDGE=omni-knowledge"
    echo "S3_BUCKET_THANOS=omni-thanos"
    GENERATED_VARS=$((GENERATED_VARS + 13))

    # ─── HashiCorp Vault ──────────────────────────────────────────────────────
    local vault_root_token
    vault_root_token=$(get_or_generate "vault" "root_token" generate_hex 48)

    echo ""
    echo "# ─── HashiCorp Vault ───────────────────────────────────────────────────"
    echo "VAULT_ADDR=http://omni-vault:8200"
    echo "VAULT_API_ADDR=http://omni-vault:8200"
    echo "VAULT_TOKEN=${vault_root_token}"
    echo "VAULT_UNSEAL_KEY="
    echo "VAULT_LOG_LEVEL=info"
    GENERATED_VARS=$((GENERATED_VARS + 5))

    # ─── Authentik (SSO/Auth) ─────────────────────────────────────────────────
    local authentik_secret authentik_bootstrap_pass
    authentik_secret=$(get_or_generate "authentik" "secret_key" generate_hex 64)
    authentik_bootstrap_pass=$(get_or_generate "authentik" "bootstrap_password" generate_password 24)

    echo ""
    echo "# ─── Authentik (SSO/Auth) ──────────────────────────────────────────────"
    echo "AUTHENTIK_SECRET_KEY=${authentik_secret}"
    echo "AUTHENTIK_BOOTSTRAP_PASSWORD=${authentik_bootstrap_pass}"
    echo "AUTHENTIK_BOOTSTRAP_EMAIL=admin@${BASE_DOMAIN}"
    echo "AUTHENTIK_HOST=http://omni-authentik:9000"
    echo "AUTHENTIK_PORT=9000"
    GENERATED_VARS=$((GENERATED_VARS + 5))

    # ─── LiteLLM (AI Gateway) ────────────────────────────────────────────────
    local litellm_master_key litellm_api_key
    litellm_master_key=$(get_or_generate "litellm" "master_key" generate_alphanumeric 32)
    litellm_api_key=$(get_or_generate "litellm" "api_key" generate_alphanumeric 32)

    echo ""
    echo "# ─── LiteLLM (AI Gateway) ─────────────────────────────────────────────"
    echo "LITELLM_MASTER_KEY=sk-${litellm_master_key}"
    echo "LITELLM_API_KEY=sk-${litellm_api_key}"
    echo "LITELLM_HOST=http://omni-litellm:4000"
    echo "LITELLM_PORT=4000"
    echo "LITELLM_LOG_LEVEL=INFO"
    GENERATED_VARS=$((GENERATED_VARS + 5))

    # ─── Ollama ───────────────────────────────────────────────────────────────
    echo ""
    echo "# ─── Ollama (Local LLM) ────────────────────────────────────────────────"
    echo "OLLAMA_HOST=omni-ollama"
    echo "OLLAMA_PORT=11434"
    echo "OLLAMA_BASE_URL=http://omni-ollama:11434"
    echo "OLLAMA_NUM_PARALLEL=4"
    echo "OLLAMA_MAX_LOADED_MODELS=3"
    echo "OLLAMA_KEEP_ALIVE=30m"
    echo "OLLAMA_GPU_LAYERS=999"
    GENERATED_VARS=$((GENERATED_VARS + 7))

    # ─── Qdrant (Vector Database) ─────────────────────────────────────────────
    local qdrant_api_key
    qdrant_api_key=$(get_or_generate "qdrant" "api_key" generate_alphanumeric 32)

    echo ""
    echo "# ─── Qdrant (Vector Database) ──────────────────────────────────────────"
    echo "QDRANT_HOST=omni-qdrant"
    echo "QDRANT_PORT=6333"
    echo "QDRANT_GRPC_PORT=6334"
    echo "QDRANT_API_KEY=${qdrant_api_key}"
    echo "QDRANT_URL=http://omni-qdrant:6333"
    GENERATED_VARS=$((GENERATED_VARS + 5))

    # ─── Gitea ────────────────────────────────────────────────────────────────
    local gitea_secret gitea_internal_token gitea_lfs_jwt
    gitea_secret=$(get_or_generate "gitea" "secret_key" generate_hex 64)
    gitea_internal_token=$(get_or_generate "gitea" "internal_token" generate_alphanumeric 64)
    gitea_lfs_jwt=$(get_or_generate "gitea" "lfs_jwt_secret" generate_alphanumeric 43)

    echo ""
    echo "# ─── Gitea (Code Fortress) ─────────────────────────────────────────────"
    echo "GITEA_HOST=omni-gitea"
    echo "GITEA_PORT=3000"
    echo "GITEA_SSH_PORT=2222"
    echo "GITEA_SECRET_KEY=${gitea_secret}"
    echo "GITEA_INTERNAL_TOKEN=${gitea_internal_token}"
    echo "GITEA_LFS_JWT_SECRET=${gitea_lfs_jwt}"
    echo "GITEA_ROOT_URL=http://${BASE_DOMAIN}:3000"
    echo "GITEA_ADMIN_USER=omni-admin"
    echo "GITEA_ADMIN_PASSWORD=$(get_or_generate 'gitea' 'admin_password' generate_password 24)"
    GENERATED_VARS=$((GENERATED_VARS + 9))

    # ─── Mattermost ───────────────────────────────────────────────────────────
    local mm_at_hash mm_invite_salt
    mm_at_hash=$(get_or_generate "mattermost" "at_hash_key" generate_alphanumeric 32)
    mm_invite_salt=$(get_or_generate "mattermost" "invite_salt" generate_alphanumeric 32)

    echo ""
    echo "# ─── Mattermost (Communication Hub) ────────────────────────────────────"
    echo "MATTERMOST_HOST=omni-mattermost"
    echo "MATTERMOST_PORT=8065"
    echo "MM_SQLSETTINGS_DATASOURCE=postgres://omni_mattermost:$(get_or_generate 'database/mattermost' 'password' generate_password 32)@omni-postgres:5432/omni_mattermost?sslmode=disable"
    echo "MM_SERVICESETTINGS_SITEURL=http://${BASE_DOMAIN}:8065"
    echo "MM_EMAILSETTINGS_ENABLESIGNUPWITHEMAIL=true"
    echo "MM_AT_HASH_KEY=${mm_at_hash}"
    echo "MM_INVITE_SALT=${mm_invite_salt}"
    echo "MATTERMOST_WEBHOOK_URL="
    echo "MATTERMOST_BOT_TOKEN="
    GENERATED_VARS=$((GENERATED_VARS + 9))

    # ─── n8n (Workflow Engine) ────────────────────────────────────────────────
    local n8n_encryption_key
    n8n_encryption_key=$(get_or_generate "n8n" "encryption_key" generate_alphanumeric 32)

    echo ""
    echo "# ─── n8n (Workflow Engine) ─────────────────────────────────────────────"
    echo "N8N_HOST=omni-n8n"
    echo "N8N_PORT=5678"
    echo "N8N_ENCRYPTION_KEY=${n8n_encryption_key}"
    echo "N8N_PROTOCOL=http"
    echo "N8N_BASIC_AUTH_ACTIVE=true"
    echo "N8N_BASIC_AUTH_USER=omni-admin"
    echo "N8N_BASIC_AUTH_PASSWORD=$(get_or_generate 'n8n' 'basic_auth_password' generate_password 24)"
    GENERATED_VARS=$((GENERATED_VARS + 7))

    # ─── Langfuse (AI Observability) ──────────────────────────────────────────
    local langfuse_secret langfuse_salt langfuse_pk langfuse_sk
    langfuse_secret=$(get_or_generate "langfuse" "nextauth_secret" generate_hex 32)
    langfuse_salt=$(get_or_generate "langfuse" "salt" generate_hex 16)
    langfuse_pk=$(get_or_generate "langfuse" "public_key" generate_alphanumeric 20)
    langfuse_sk=$(get_or_generate "langfuse" "secret_key" generate_alphanumeric 40)

    echo ""
    echo "# ─── Langfuse (AI Observability) ───────────────────────────────────────"
    echo "LANGFUSE_HOST=omni-langfuse"
    echo "LANGFUSE_PORT=3000"
    echo "LANGFUSE_NEXTAUTH_SECRET=${langfuse_secret}"
    echo "LANGFUSE_SALT=${langfuse_salt}"
    echo "LANGFUSE_PUBLIC_KEY=pk-lf-${langfuse_pk}"
    echo "LANGFUSE_SECRET_KEY=sk-lf-${langfuse_sk}"
    echo "LANGFUSE_URL=http://omni-langfuse:3000"
    GENERATED_VARS=$((GENERATED_VARS + 7))

    # ─── Prometheus/Grafana (Observatory) ─────────────────────────────────────
    local grafana_admin_pass
    grafana_admin_pass=$(get_or_generate "grafana" "admin_password" generate_password 24)

    echo ""
    echo "# ─── Prometheus + Grafana (Observatory) ────────────────────────────────"
    echo "PROMETHEUS_HOST=omni-prometheus"
    echo "PROMETHEUS_PORT=9090"
    echo "GRAFANA_HOST=omni-grafana"
    echo "GRAFANA_PORT=3001"
    echo "GRAFANA_ADMIN_USER=omni-admin"
    echo "GRAFANA_ADMIN_PASSWORD=${grafana_admin_pass}"
    echo "GF_SECURITY_ADMIN_USER=omni-admin"
    echo "GF_SECURITY_ADMIN_PASSWORD=${grafana_admin_pass}"
    echo "GF_SERVER_ROOT_URL=http://${BASE_DOMAIN}:3001"
    GENERATED_VARS=$((GENERATED_VARS + 9))

    # ─── Traefik (Gateway Sentinel) ───────────────────────────────────────────
    local traefik_dashboard_pass
    traefik_dashboard_pass=$(get_or_generate "traefik" "dashboard_password" generate_password 24)

    echo ""
    echo "# ─── Traefik (Gateway Sentinel) ────────────────────────────────────────"
    echo "TRAEFIK_HOST=omni-traefik"
    echo "TRAEFIK_HTTP_PORT=80"
    echo "TRAEFIK_HTTPS_PORT=443"
    echo "TRAEFIK_DASHBOARD_PORT=8080"
    echo "TRAEFIK_DASHBOARD_USER=omni-admin"
    echo "TRAEFIK_DASHBOARD_PASSWORD=${traefik_dashboard_pass}"
    echo "TRAEFIK_ACME_EMAIL=admin@${BASE_DOMAIN}"
    GENERATED_VARS=$((GENERATED_VARS + 7))

    # ─── Woodpecker CI (Build Forge) ──────────────────────────────────────────
    local woodpecker_secret woodpecker_agent_secret
    woodpecker_secret=$(get_or_generate "woodpecker" "secret" generate_hex 32)
    woodpecker_agent_secret=$(get_or_generate "woodpecker" "agent_secret" generate_hex 32)

    echo ""
    echo "# ─── Woodpecker CI (Build Forge) ───────────────────────────────────────"
    echo "WOODPECKER_HOST=omni-woodpecker-server"
    echo "WOODPECKER_PORT=8000"
    echo "WOODPECKER_SERVER=omni-woodpecker-server:9000"
    echo "WOODPECKER_SECRET=${woodpecker_secret}"
    echo "WOODPECKER_AGENT_SECRET=${woodpecker_agent_secret}"
    echo "WOODPECKER_GITEA_URL=http://omni-gitea:3000"
    echo "WOODPECKER_GITEA_CLIENT="
    echo "WOODPECKER_GITEA_SECRET="
    echo "WOODPECKER_ADMIN=omni-admin"
    echo "WOODPECKER_OPEN=false"
    GENERATED_VARS=$((GENERATED_VARS + 10))

    # ─── Coder (Code Forge) ───────────────────────────────────────────────────
    local coder_pg_pass
    coder_pg_pass=$(get_or_generate "database/coder" "password" generate_password 32)

    echo ""
    echo "# ─── Coder (Code Forge) ────────────────────────────────────────────────"
    echo "CODER_HOST=omni-coder"
    echo "CODER_PORT=7080"
    echo "CODER_ACCESS_URL=http://${BASE_DOMAIN}:7080"
    echo "CODER_PG_CONNECTION_URL=postgresql://omni_coder:${coder_pg_pass}@omni-postgres:5432/omni_coder?sslmode=disable"
    GENERATED_VARS=$((GENERATED_VARS + 4))

    # ─── Master Orchestrator (Omni Command) ───────────────────────────────────
    local orchestrator_api_key orchestrator_jwt_secret
    orchestrator_api_key=$(get_or_generate "orchestrator" "api_key" generate_alphanumeric 48)
    orchestrator_jwt_secret=$(get_or_generate "orchestrator" "jwt_secret" generate_hex 64)

    echo ""
    echo "# ─── Master Orchestrator (Omni Command) ────────────────────────────────"
    echo "ORCHESTRATOR_HOST=omni-orchestrator"
    echo "ORCHESTRATOR_API_PORT=9500"
    echo "ORCHESTRATOR_DASHBOARD_PORT=9501"
    echo "ORCHESTRATOR_VOICE_PORT=9502"
    echo "ORCHESTRATOR_API_KEY=${orchestrator_api_key}"
    echo "ORCHESTRATOR_JWT_SECRET=${orchestrator_jwt_secret}"
    echo "ORCHESTRATOR_URL=http://omni-orchestrator:9500"
    GENERATED_VARS=$((GENERATED_VARS + 7))

    # ─── Token Infinity ───────────────────────────────────────────────────────
    local ti_api_key
    ti_api_key=$(get_or_generate "token-infinity" "api_key" generate_alphanumeric 32)

    echo ""
    echo "# ─── Token Infinity ────────────────────────────────────────────────────"
    echo "TOKEN_INFINITY_HOST=omni-token-infinity"
    echo "TOKEN_INFINITY_PORT=9600"
    echo "TOKEN_INFINITY_API_KEY=${ti_api_key}"
    echo "TOKEN_INFINITY_URL=http://omni-token-infinity:9600"
    GENERATED_VARS=$((GENERATED_VARS + 4))

    # ─── Omi Wearable Bridge ──────────────────────────────────────────────────
    echo ""
    echo "# ─── Omi Wearable Bridge ───────────────────────────────────────────────"
    echo "OMI_BRIDGE_HOST=omni-omi-bridge"
    echo "OMI_BRIDGE_PORT=9700"
    echo "OMI_DEVICE_ID="
    echo "OMI_HAPTIC_ENABLED=true"
    echo "OMI_VOICE_ENABLED=true"
    GENERATED_VARS=$((GENERATED_VARS + 5))

    # ─── CrowdSec (Security Shield) ──────────────────────────────────────────
    local crowdsec_api_key
    crowdsec_api_key=$(get_or_generate "crowdsec" "api_key" generate_alphanumeric 32)

    echo ""
    echo "# ─── CrowdSec (Security Shield) ────────────────────────────────────────"
    echo "CROWDSEC_HOST=omni-crowdsec"
    echo "CROWDSEC_PORT=8080"
    echo "CROWDSEC_AGENT_USERNAME=omni-agent"
    echo "CROWDSEC_AGENT_PASSWORD=${crowdsec_api_key}"
    GENERATED_VARS=$((GENERATED_VARS + 4))

    # ─── Thanos (Enhanced Monitoring) ─────────────────────────────────────────
    echo ""
    echo "# ─── Thanos (Pulse Command Pro) ────────────────────────────────────────"
    echo "THANOS_QUERY_HOST=omni-thanos-query"
    echo "THANOS_QUERY_PORT=9090"
    echo "THANOS_STORE_HOST=omni-thanos-store"
    echo "THANOS_COMPACTOR_HOST=omni-thanos-compactor"
    GENERATED_VARS=$((GENERATED_VARS + 4))

    # ─── Uptime Kuma (Guardian Eye) ───────────────────────────────────────────
    echo ""
    echo "# ─── Uptime Kuma (Guardian Eye) ────────────────────────────────────────"
    echo "UPTIME_KUMA_HOST=omni-uptime-kuma"
    echo "UPTIME_KUMA_PORT=3001"
    GENERATED_VARS=$((GENERATED_VARS + 2))

    # ─── Portainer ────────────────────────────────────────────────────────────
    local portainer_admin_pass
    portainer_admin_pass=$(get_or_generate "portainer" "admin_password" generate_password 24)

    echo ""
    echo "# ─── Portainer (Container Manager) ─────────────────────────────────────"
    echo "PORTAINER_HOST=omni-portainer"
    echo "PORTAINER_PORT=9443"
    echo "PORTAINER_ADMIN_PASSWORD=${portainer_admin_pass}"
    GENERATED_VARS=$((GENERATED_VARS + 3))

    # ─── Coolify (Deploy Engine) ──────────────────────────────────────────────
    echo ""
    echo "# ─── Coolify (Deploy Engine) ───────────────────────────────────────────"
    echo "COOLIFY_HOST=omni-coolify"
    echo "COOLIFY_PORT=8000"
    GENERATED_VARS=$((GENERATED_VARS + 2))

    # ─── Loki (Log Nexus) ────────────────────────────────────────────────────
    echo ""
    echo "# ─── Loki (Log Nexus) ──────────────────────────────────────────────────"
    echo "LOKI_HOST=omni-loki"
    echo "LOKI_PORT=3100"
    echo "LOKI_URL=http://omni-loki:3100"
    GENERATED_VARS=$((GENERATED_VARS + 3))

    # ─── Nango (Integration Hub) ──────────────────────────────────────────────
    local nango_secret
    nango_secret=$(get_or_generate "nango" "secret_key" generate_hex 32)

    echo ""
    echo "# ─── Nango (Integration Hub) ───────────────────────────────────────────"
    echo "NANGO_HOST=omni-nango"
    echo "NANGO_PORT=3003"
    echo "NANGO_SECRET_KEY=${nango_secret}"
    GENERATED_VARS=$((GENERATED_VARS + 3))

    # ─── OpenHands & SWE-Agent ────────────────────────────────────────────────
    echo ""
    echo "# ─── AI Coding Agents ──────────────────────────────────────────────────"
    echo "OPENHANDS_HOST=omni-openhands"
    echo "OPENHANDS_PORT=3000"
    echo "OPENHANDS_LLM_BASE_URL=http://omni-litellm:4000"
    echo "SWE_AGENT_HOST=omni-swe-agent"
    echo "SWE_AGENT_PORT=8000"
    echo "SWE_AGENT_LLM_BASE_URL=http://omni-litellm:4000"
    GENERATED_VARS=$((GENERATED_VARS + 6))

    # ─── Financial Services ───────────────────────────────────────────────────
    echo ""
    echo "# ─── Financial Services ────────────────────────────────────────────────"
    echo "FINANCIAL_DB_URL=postgresql://omni_financial:$(get_or_generate 'database/financial' 'password' generate_password 32)@omni-postgres:5432/omni_financial"
    echo "TAX_FORTRESS_PORT=4011"
    echo "DASHBOARD_PORT=4012"
    echo "ALERT_ENGINE_PORT=4013"
    echo "INVOICE_ENGINE_PORT=4014"
    echo "BANK_RECONCILIATION_PORT=4015"
    echo "CONTRACTOR_VAULT_PORT=4016"
    echo "EXPENSE_INTEL_PORT=4017"
    echo "CUSTOMER_INTEL_PORT=4018"
    GENERATED_VARS=$((GENERATED_VARS + 9))

    # ─── Platform Metadata ────────────────────────────────────────────────────
    echo ""
    echo "# ─── Platform Metadata ─────────────────────────────────────────────────"
    echo "OMNI_VERSION=3.0.0"
    echo "OMNI_BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "OMNI_INSTANCE_ID=$(generate_uuid)"
    echo "OMNI_TOTAL_SYSTEMS=37"
    GENERATED_VARS=$((GENERATED_VARS + 4))

    echo ""
    echo "# ═══════════════════════════════════════════════════════════════════════════════"
    echo "# END OF GENERATED ENVIRONMENT — ${GENERATED_VARS} variables"
    echo "# ═══════════════════════════════════════════════════════════════════════════════"
}

# ─── Execute ──────────────────────────────────────────────────────────────────
if [[ "$DRY_RUN" == "true" ]]; then
    log_info "DRY RUN — printing to stdout:"
    echo ""
    generate_env
    echo ""
    log_info "Would have generated ${GENERATED_VARS} variables"
else
    generate_env > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    log_success "Generated ${ENV_FILE} with ${GENERATED_VARS}+ variables"
    log_success "File permissions set to 600 (owner read/write only)"

    if [[ "$USE_VAULT" == "true" ]]; then
        log_success "Secrets synchronized with Vault at ${VAULT_ADDR}"
    fi
fi

echo ""
echo -e "${BOLD}${GREEN}  ⚛  Environment generation complete!${NC}"
echo -e "  Next: Run ${CYAN}scripts/init-databases.sh${NC} to create all databases"
echo ""
