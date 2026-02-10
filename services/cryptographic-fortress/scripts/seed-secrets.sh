#!/usr/bin/env bash
###############################################################################
# seed-secrets.sh - Seed master environment values into Vault KV v2
#
# System 2: Cryptographic Fortress
#
# Reads secrets from environment variables and stores them in Vault at
# secret/data/{service} paths. Designed for initial bootstrap.
###############################################################################
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
export VAULT_ADDR

KV_MOUNT="secret"

# ---------------------------------------------------------------------------
# Colored timestamped output
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [ERROR]${NC} $*"; }
log_step()  { echo -e "${CYAN}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [STEP]${NC}  $*"; }

# ---------------------------------------------------------------------------
# Cleanup trap
# ---------------------------------------------------------------------------
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "seed-secrets.sh exited with code $exit_code"
    fi
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
validate_prereqs() {
    log_step "Validating prerequisites"

    if ! command -v vault &>/dev/null; then
        log_error "vault CLI not found in PATH"
        return 1
    fi

    if [[ -z "${VAULT_TOKEN:-}" ]]; then
        log_error "VAULT_TOKEN is not set. Authenticate to Vault first."
        return 1
    fi

    # Verify KV engine is mounted
    if ! vault secrets list -format=json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if '${KV_MOUNT}/' in d else 1)" 2>/dev/null; then
        log_error "KV v2 engine not mounted at ${KV_MOUNT}/. Run vault-init.sh first."
        return 1
    fi

    log_ok "Prerequisites validated"
}

# ---------------------------------------------------------------------------
# Helper: write a secret (KV v2)
# ---------------------------------------------------------------------------
STORED_PATHS=()
STORED_COUNT=0
SKIPPED_COUNT=0

write_secret() {
    local path="$1"
    shift
    # Remaining args are key=value pairs

    local kv_pairs=()
    local has_value=false

    for pair in "$@"; do
        local key="${pair%%=*}"
        local env_var="${pair#*=}"
        local value="${!env_var:-}"

        if [[ -n "$value" ]]; then
            kv_pairs+=("${key}=${value}")
            has_value=true
        else
            log_warn "  env var ${env_var} is empty -- key '${key}' will be omitted"
        fi
    done

    if [[ "$has_value" == "false" ]]; then
        log_warn "  No values set for ${path} -- skipping"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        return 0
    fi

    if vault kv put "${KV_MOUNT}/${path}" "${kv_pairs[@]}" &>/dev/null; then
        log_ok "  Stored: ${KV_MOUNT}/${path}"
        STORED_PATHS+=("${KV_MOUNT}/data/${path}")
        STORED_COUNT=$((STORED_COUNT + 1))
    else
        log_error "  Failed to store: ${KV_MOUNT}/${path}"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Seed: PostgreSQL
# ---------------------------------------------------------------------------
seed_postgresql() {
    log_step "Seeding PostgreSQL secrets"
    write_secret "postgresql/connection" \
        "host=POSTGRES_HOST" \
        "port=POSTGRES_PORT" \
        "admin_user=POSTGRES_USER" \
        "admin_password=POSTGRES_PASSWORD" \
        "ssl_mode=POSTGRES_SSL_MODE"
}

# ---------------------------------------------------------------------------
# Seed: Redis
# ---------------------------------------------------------------------------
seed_redis() {
    log_step "Seeding Redis secrets"
    write_secret "redis/connection" \
        "host=REDIS_HOST" \
        "port=REDIS_PORT" \
        "password=REDIS_PASSWORD" \
        "tls_enabled=REDIS_TLS_ENABLED"
}

# ---------------------------------------------------------------------------
# Seed: MinIO
# ---------------------------------------------------------------------------
seed_minio() {
    log_step "Seeding MinIO secrets"
    write_secret "minio/connection" \
        "endpoint=MINIO_ENDPOINT" \
        "access_key=MINIO_ACCESS_KEY" \
        "secret_key=MINIO_SECRET_KEY" \
        "region=MINIO_REGION" \
        "use_ssl=MINIO_USE_SSL"
}

# ---------------------------------------------------------------------------
# Seed: Gitea
# ---------------------------------------------------------------------------
seed_gitea() {
    log_step "Seeding Gitea secrets"
    write_secret "gitea/config" \
        "db_type=GITEA_DB_TYPE" \
        "db_host=GITEA_DB_HOST" \
        "db_name=GITEA_DB_NAME" \
        "db_user=GITEA_DB_USER" \
        "db_password=GITEA_DB_PASSWORD" \
        "secret_key=GITEA_SECRET_KEY" \
        "internal_token=GITEA_INTERNAL_TOKEN" \
        "lfs_jwt_secret=GITEA_LFS_JWT_SECRET"
    write_secret "gitea/token" \
        "admin_token=GITEA_ADMIN_TOKEN"
}

# ---------------------------------------------------------------------------
# Seed: Mattermost
# ---------------------------------------------------------------------------
seed_mattermost() {
    log_step "Seeding Mattermost secrets"
    write_secret "mattermost/config" \
        "db_host=MATTERMOST_DB_HOST" \
        "db_name=MATTERMOST_DB_NAME" \
        "db_user=MATTERMOST_DB_USER" \
        "db_password=MATTERMOST_DB_PASSWORD" \
        "site_url=MATTERMOST_SITE_URL" \
        "smtp_user=MATTERMOST_SMTP_USER" \
        "smtp_password=MATTERMOST_SMTP_PASSWORD"
    write_secret "mattermost/webhook" \
        "security_alerts_webhook=MATTERMOST_SECURITY_WEBHOOK"
}

# ---------------------------------------------------------------------------
# Seed: LiteLLM
# ---------------------------------------------------------------------------
seed_litellm() {
    log_step "Seeding LiteLLM secrets"
    write_secret "litellm/config" \
        "master_key=LITELLM_MASTER_KEY" \
        "database_url=LITELLM_DATABASE_URL" \
        "redis_host=LITELLM_REDIS_HOST" \
        "redis_password=LITELLM_REDIS_PASSWORD"
    write_secret "api-keys/openai" \
        "api_key=OPENAI_API_KEY" \
        "org_id=OPENAI_ORG_ID"
    write_secret "api-keys/anthropic" \
        "api_key=ANTHROPIC_API_KEY"
    write_secret "api-keys/google" \
        "api_key=GOOGLE_AI_API_KEY"
    write_secret "api-keys/azure-openai" \
        "api_key=AZURE_OPENAI_API_KEY" \
        "endpoint=AZURE_OPENAI_ENDPOINT" \
        "api_version=AZURE_OPENAI_API_VERSION"
}

# ---------------------------------------------------------------------------
# Seed: Langfuse
# ---------------------------------------------------------------------------
seed_langfuse() {
    log_step "Seeding Langfuse secrets"
    write_secret "langfuse/config" \
        "database_url=LANGFUSE_DATABASE_URL" \
        "nextauth_secret=LANGFUSE_NEXTAUTH_SECRET" \
        "nextauth_url=LANGFUSE_NEXTAUTH_URL" \
        "salt=LANGFUSE_SALT" \
        "encryption_key=LANGFUSE_ENCRYPTION_KEY"
}

# ---------------------------------------------------------------------------
# Seed: n8n
# ---------------------------------------------------------------------------
seed_n8n() {
    log_step "Seeding n8n secrets"
    write_secret "n8n/config" \
        "db_type=N8N_DB_TYPE" \
        "db_host=N8N_DB_HOST" \
        "db_port=N8N_DB_PORT" \
        "db_name=N8N_DB_NAME" \
        "db_user=N8N_DB_USER" \
        "db_password=N8N_DB_PASSWORD" \
        "encryption_key=N8N_ENCRYPTION_KEY" \
        "webhook_url=N8N_WEBHOOK_URL"
}

# ---------------------------------------------------------------------------
# Seed: OMI (Orchestrator)
# ---------------------------------------------------------------------------
seed_omi() {
    log_step "Seeding OMI / Orchestrator secrets"
    write_secret "omi-bridge/config" \
        "api_key=OMI_API_KEY" \
        "webhook_secret=OMI_WEBHOOK_SECRET"
    write_secret "orchestrator/config" \
        "master_key=ORCHESTRATOR_MASTER_KEY" \
        "vault_role_id=ORCHESTRATOR_VAULT_ROLE_ID" \
        "vault_secret_id=ORCHESTRATOR_VAULT_SECRET_ID"
}

# ---------------------------------------------------------------------------
# Seed: Authentik
# ---------------------------------------------------------------------------
seed_authentik() {
    log_step "Seeding Authentik secrets"
    write_secret "authentik/config" \
        "secret_key=AUTHENTIK_SECRET_KEY" \
        "db_host=AUTHENTIK_DB_HOST" \
        "db_name=AUTHENTIK_DB_NAME" \
        "db_user=AUTHENTIK_DB_USER" \
        "db_password=AUTHENTIK_DB_PASSWORD" \
        "redis_url=AUTHENTIK_REDIS_URL" \
        "email_host=AUTHENTIK_EMAIL_HOST" \
        "email_username=AUTHENTIK_EMAIL_USERNAME" \
        "email_password=AUTHENTIK_EMAIL_PASSWORD"
}

# ---------------------------------------------------------------------------
# Seed: Grafana
# ---------------------------------------------------------------------------
seed_grafana() {
    log_step "Seeding Grafana secrets"
    write_secret "grafana/config" \
        "admin_user=GRAFANA_ADMIN_USER" \
        "admin_password=GRAFANA_ADMIN_PASSWORD" \
        "secret_key=GRAFANA_SECRET_KEY" \
        "smtp_host=GRAFANA_SMTP_HOST" \
        "smtp_user=GRAFANA_SMTP_USER" \
        "smtp_password=GRAFANA_SMTP_PASSWORD"
}

# ---------------------------------------------------------------------------
# Seed: Traefik
# ---------------------------------------------------------------------------
seed_traefik() {
    log_step "Seeding Traefik secrets"
    write_secret "traefik/config" \
        "dashboard_user=TRAEFIK_DASHBOARD_USER" \
        "dashboard_password=TRAEFIK_DASHBOARD_PASSWORD" \
        "acme_email=TRAEFIK_ACME_EMAIL" \
        "cf_api_token=TRAEFIK_CF_API_TOKEN"
}

# ---------------------------------------------------------------------------
# Seed: Prometheus
# ---------------------------------------------------------------------------
seed_prometheus() {
    log_step "Seeding Prometheus secrets"
    write_secret "prometheus/config" \
        "remote_write_url=PROMETHEUS_REMOTE_WRITE_URL" \
        "remote_write_user=PROMETHEUS_REMOTE_WRITE_USER" \
        "remote_write_password=PROMETHEUS_REMOTE_WRITE_PASSWORD" \
        "alertmanager_webhook=PROMETHEUS_ALERTMANAGER_WEBHOOK"
}

# ---------------------------------------------------------------------------
# Seed: Woodpecker
# ---------------------------------------------------------------------------
seed_woodpecker() {
    log_step "Seeding Woodpecker secrets"
    write_secret "woodpecker/config" \
        "agent_secret=WOODPECKER_AGENT_SECRET" \
        "gitea_url=WOODPECKER_GITEA_URL" \
        "gitea_client_id=WOODPECKER_GITEA_CLIENT_ID" \
        "gitea_client_secret=WOODPECKER_GITEA_CLIENT_SECRET" \
        "db_driver=WOODPECKER_DB_DRIVER" \
        "db_datasource=WOODPECKER_DB_DATASOURCE"
}

# ---------------------------------------------------------------------------
# Seed: OpenHands
# ---------------------------------------------------------------------------
seed_openhands() {
    log_step "Seeding OpenHands secrets"
    write_secret "openhands/config" \
        "llm_api_base=OPENHANDS_LLM_API_BASE" \
        "llm_api_key=OPENHANDS_LLM_API_KEY" \
        "sandbox_runtime=OPENHANDS_SANDBOX_RUNTIME" \
        "workspace_mount=OPENHANDS_WORKSPACE_MOUNT"
}

# ---------------------------------------------------------------------------
# Seed: SWE-Agent
# ---------------------------------------------------------------------------
seed_swe_agent() {
    log_step "Seeding SWE-Agent secrets"
    write_secret "swe-agent/config" \
        "llm_api_base=SWE_AGENT_LLM_API_BASE" \
        "llm_api_key=SWE_AGENT_LLM_API_KEY" \
        "github_token=SWE_AGENT_GITHUB_TOKEN"
}

# ---------------------------------------------------------------------------
# Seed: Plane
# ---------------------------------------------------------------------------
seed_plane() {
    log_step "Seeding Plane secrets"
    write_secret "plane/config" \
        "secret_key=PLANE_SECRET_KEY" \
        "db_host=PLANE_DB_HOST" \
        "db_name=PLANE_DB_NAME" \
        "db_user=PLANE_DB_USER" \
        "db_password=PLANE_DB_PASSWORD" \
        "redis_url=PLANE_REDIS_URL"
}

# ---------------------------------------------------------------------------
# Seed: Wiki.js
# ---------------------------------------------------------------------------
seed_wikijs() {
    log_step "Seeding Wiki.js secrets"
    write_secret "wikijs/config" \
        "db_host=WIKIJS_DB_HOST" \
        "db_name=WIKIJS_DB_NAME" \
        "db_user=WIKIJS_DB_USER" \
        "db_password=WIKIJS_DB_PASSWORD" \
        "admin_email=WIKIJS_ADMIN_EMAIL" \
        "admin_password=WIKIJS_ADMIN_PASSWORD"
}

# ---------------------------------------------------------------------------
# Seed: Superset
# ---------------------------------------------------------------------------
seed_superset() {
    log_step "Seeding Superset secrets"
    write_secret "superset/config" \
        "secret_key=SUPERSET_SECRET_KEY" \
        "db_host=SUPERSET_DB_HOST" \
        "db_name=SUPERSET_DB_NAME" \
        "db_user=SUPERSET_DB_USER" \
        "db_password=SUPERSET_DB_PASSWORD" \
        "admin_user=SUPERSET_ADMIN_USER" \
        "admin_password=SUPERSET_ADMIN_PASSWORD"
}

# ---------------------------------------------------------------------------
# Seed: Cal.com
# ---------------------------------------------------------------------------
seed_calcom() {
    log_step "Seeding Cal.com secrets"
    write_secret "calcom/config" \
        "database_url=CALCOM_DATABASE_URL" \
        "nextauth_secret=CALCOM_NEXTAUTH_SECRET" \
        "calendso_encryption_key=CALCOM_ENCRYPTION_KEY"
}

# ---------------------------------------------------------------------------
# Seed: Twenty
# ---------------------------------------------------------------------------
seed_twenty() {
    log_step "Seeding Twenty CRM secrets"
    write_secret "twenty/config" \
        "db_host=TWENTY_DB_HOST" \
        "db_name=TWENTY_DB_NAME" \
        "db_user=TWENTY_DB_USER" \
        "db_password=TWENTY_DB_PASSWORD" \
        "access_token_secret=TWENTY_ACCESS_TOKEN_SECRET" \
        "refresh_token_secret=TWENTY_REFRESH_TOKEN_SECRET" \
        "login_token_secret=TWENTY_LOGIN_TOKEN_SECRET"
}

# ---------------------------------------------------------------------------
# Seed: Crater
# ---------------------------------------------------------------------------
seed_crater() {
    log_step "Seeding Crater secrets"
    write_secret "crater/config" \
        "db_host=CRATER_DB_HOST" \
        "db_name=CRATER_DB_NAME" \
        "db_user=CRATER_DB_USER" \
        "db_password=CRATER_DB_PASSWORD" \
        "app_key=CRATER_APP_KEY" \
        "mail_host=CRATER_MAIL_HOST" \
        "mail_username=CRATER_MAIL_USERNAME" \
        "mail_password=CRATER_MAIL_PASSWORD"
}

# ---------------------------------------------------------------------------
# Seed: CrowdSec
# ---------------------------------------------------------------------------
seed_crowdsec() {
    log_step "Seeding CrowdSec secrets"
    write_secret "crowdsec/config" \
        "api_key=CROWDSEC_API_KEY" \
        "bouncer_key=CROWDSEC_BOUNCER_KEY" \
        "enroll_key=CROWDSEC_ENROLL_KEY"
}

# ---------------------------------------------------------------------------
# Seed: Portainer
# ---------------------------------------------------------------------------
seed_portainer() {
    log_step "Seeding Portainer secrets"
    write_secret "portainer/config" \
        "admin_password=PORTAINER_ADMIN_PASSWORD" \
        "edge_key=PORTAINER_EDGE_KEY"
}

# ---------------------------------------------------------------------------
# Seed: Coder
# ---------------------------------------------------------------------------
seed_coder() {
    log_step "Seeding Coder secrets"
    write_secret "coder/config" \
        "access_url=CODER_ACCESS_URL" \
        "pg_connection_url=CODER_PG_CONNECTION_URL" \
        "oidc_client_id=CODER_OIDC_CLIENT_ID" \
        "oidc_client_secret=CODER_OIDC_CLIENT_SECRET"
}

# ---------------------------------------------------------------------------
# Seed: Qdrant
# ---------------------------------------------------------------------------
seed_qdrant() {
    log_step "Seeding Qdrant secrets"
    write_secret "qdrant/config" \
        "api_key=QDRANT_API_KEY" \
        "host=QDRANT_HOST" \
        "port=QDRANT_PORT"
}

# ---------------------------------------------------------------------------
# Seed: Ollama
# ---------------------------------------------------------------------------
seed_ollama() {
    log_step "Seeding Ollama secrets"
    write_secret "ollama/config" \
        "host=OLLAMA_HOST" \
        "api_key=OLLAMA_API_KEY"
}

# ---------------------------------------------------------------------------
# Seed: Nango
# ---------------------------------------------------------------------------
seed_nango() {
    log_step "Seeding Nango secrets"
    write_secret "nango/config" \
        "secret_key=NANGO_SECRET_KEY" \
        "db_host=NANGO_DB_HOST" \
        "db_password=NANGO_DB_PASSWORD" \
        "encryption_key=NANGO_ENCRYPTION_KEY" \
        "callback_url=NANGO_CALLBACK_URL"
}

# ---------------------------------------------------------------------------
# Seed: Flowise
# ---------------------------------------------------------------------------
seed_flowise() {
    log_step "Seeding Flowise secrets"
    write_secret "flowise/config" \
        "username=FLOWISE_USERNAME" \
        "password=FLOWISE_PASSWORD" \
        "secretkey_overwrite=FLOWISE_SECRETKEY" \
        "database_path=FLOWISE_DATABASE_PATH"
}

# ---------------------------------------------------------------------------
# Seed: Token Infinity
# ---------------------------------------------------------------------------
seed_token_infinity() {
    log_step "Seeding Token Infinity secrets"
    write_secret "token-infinity/config" \
        "master_key=TOKEN_INFINITY_MASTER_KEY" \
        "encryption_key=TOKEN_INFINITY_ENCRYPTION_KEY"
}

# ---------------------------------------------------------------------------
# Seed: Thanos
# ---------------------------------------------------------------------------
seed_thanos() {
    log_step "Seeding Thanos secrets"
    write_secret "thanos/config" \
        "s3_endpoint=THANOS_S3_ENDPOINT" \
        "s3_access_key=THANOS_S3_ACCESS_KEY" \
        "s3_secret_key=THANOS_S3_SECRET_KEY" \
        "s3_bucket=THANOS_S3_BUCKET"
}

# ---------------------------------------------------------------------------
# Seed: Uptime Kuma
# ---------------------------------------------------------------------------
seed_uptime_kuma() {
    log_step "Seeding Uptime Kuma secrets"
    write_secret "uptime-kuma/config" \
        "admin_password=UPTIME_KUMA_ADMIN_PASSWORD" \
        "notification_webhook=UPTIME_KUMA_NOTIFICATION_WEBHOOK"
}

# ---------------------------------------------------------------------------
# Seed: Coolify
# ---------------------------------------------------------------------------
seed_coolify() {
    log_step "Seeding Coolify secrets"
    write_secret "coolify/config" \
        "app_key=COOLIFY_APP_KEY" \
        "db_password=COOLIFY_DB_PASSWORD" \
        "pusher_app_key=COOLIFY_PUSHER_APP_KEY" \
        "pusher_app_secret=COOLIFY_PUSHER_APP_SECRET"
}

# ---------------------------------------------------------------------------
# Seed: MLflow
# ---------------------------------------------------------------------------
seed_mlflow() {
    log_step "Seeding MLflow secrets"
    write_secret "mlflow/config" \
        "backend_store_uri=MLFLOW_BACKEND_STORE_URI" \
        "artifact_root=MLFLOW_ARTIFACT_ROOT" \
        "s3_access_key=MLFLOW_S3_ACCESS_KEY" \
        "s3_secret_key=MLFLOW_S3_SECRET_KEY"
}

# ---------------------------------------------------------------------------
# Seed: Keycloak
# ---------------------------------------------------------------------------
seed_keycloak() {
    log_step "Seeding Keycloak secrets"
    write_secret "keycloak/config" \
        "admin_user=KEYCLOAK_ADMIN_USER" \
        "admin_password=KEYCLOAK_ADMIN_PASSWORD" \
        "db_host=KEYCLOAK_DB_HOST" \
        "db_name=KEYCLOAK_DB_NAME" \
        "db_user=KEYCLOAK_DB_USER" \
        "db_password=KEYCLOAK_DB_PASSWORD"
}

# ---------------------------------------------------------------------------
# Seed: GlitchTip
# ---------------------------------------------------------------------------
seed_glitchtip() {
    log_step "Seeding GlitchTip secrets"
    write_secret "glitchtip/config" \
        "secret_key=GLITCHTIP_SECRET_KEY" \
        "database_url=GLITCHTIP_DATABASE_URL" \
        "redis_url=GLITCHTIP_REDIS_URL" \
        "email_url=GLITCHTIP_EMAIL_URL"
}

# ---------------------------------------------------------------------------
# Seed: Listmonk
# ---------------------------------------------------------------------------
seed_listmonk() {
    log_step "Seeding Listmonk secrets"
    write_secret "listmonk/config" \
        "admin_user=LISTMONK_ADMIN_USER" \
        "admin_password=LISTMONK_ADMIN_PASSWORD" \
        "db_host=LISTMONK_DB_HOST" \
        "db_name=LISTMONK_DB_NAME" \
        "db_user=LISTMONK_DB_USER" \
        "db_password=LISTMONK_DB_PASSWORD"
}

# ---------------------------------------------------------------------------
# Seed: Chatwoot
# ---------------------------------------------------------------------------
seed_chatwoot() {
    log_step "Seeding Chatwoot secrets"
    write_secret "chatwoot/config" \
        "secret_key_base=CHATWOOT_SECRET_KEY_BASE" \
        "frontend_url=CHATWOOT_FRONTEND_URL" \
        "db_host=CHATWOOT_DB_HOST" \
        "db_name=CHATWOOT_DB_NAME" \
        "db_user=CHATWOOT_DB_USER" \
        "db_password=CHATWOOT_DB_PASSWORD" \
        "redis_url=CHATWOOT_REDIS_URL"
}

# ---------------------------------------------------------------------------
# Seed: Pact Broker
# ---------------------------------------------------------------------------
seed_pact_broker() {
    log_step "Seeding Pact Broker secrets"
    write_secret "pact-broker/config" \
        "db_host=PACT_BROKER_DB_HOST" \
        "db_name=PACT_BROKER_DB_NAME" \
        "db_user=PACT_BROKER_DB_USER" \
        "db_password=PACT_BROKER_DB_PASSWORD" \
        "basic_auth_username=PACT_BROKER_BASIC_AUTH_USERNAME" \
        "basic_auth_password=PACT_BROKER_BASIC_AUTH_PASSWORD"
}

# ---------------------------------------------------------------------------
# Seed: Formbricks
# ---------------------------------------------------------------------------
seed_formbricks() {
    log_step "Seeding Formbricks secrets"
    write_secret "formbricks/config" \
        "database_url=FORMBRICKS_DATABASE_URL" \
        "nextauth_secret=FORMBRICKS_NEXTAUTH_SECRET" \
        "nextauth_url=FORMBRICKS_NEXTAUTH_URL" \
        "encryption_key=FORMBRICKS_ENCRYPTION_KEY"
}

# ---------------------------------------------------------------------------
# Seed: Tolgee
# ---------------------------------------------------------------------------
seed_tolgee() {
    log_step "Seeding Tolgee secrets"
    write_secret "tolgee/config" \
        "jwt_secret=TOLGEE_JWT_SECRET" \
        "db_host=TOLGEE_DB_HOST" \
        "db_name=TOLGEE_DB_NAME" \
        "db_user=TOLGEE_DB_USER" \
        "db_password=TOLGEE_DB_PASSWORD"
}

# ---------------------------------------------------------------------------
# Output summary
# ---------------------------------------------------------------------------
output_summary() {
    echo ""
    echo "======================================================================"
    echo " Secret Seeding Summary"
    echo "======================================================================"
    echo ""
    echo "  Stored : ${STORED_COUNT}"
    echo "  Skipped: ${SKIPPED_COUNT}"
    echo ""

    if [[ ${#STORED_PATHS[@]} -gt 0 ]]; then
        echo "  Stored paths:"
        for path in "${STORED_PATHS[@]}"; do
            echo "    - ${path}"
        done
    fi

    echo ""
    echo "  Verify a secret:"
    echo "    vault kv get ${KV_MOUNT}/postgresql/connection"
    echo ""
    echo "======================================================================"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo "======================================================================"
    echo " Omni-Quantum Elite: Secret Seeding"
    echo " Vault Address: ${VAULT_ADDR}"
    echo " KV Mount: ${KV_MOUNT}"
    echo "======================================================================"
    echo ""

    validate_prereqs

    # Core infrastructure
    seed_postgresql
    seed_redis
    seed_minio

    # Primary services
    seed_gitea
    seed_mattermost
    seed_litellm
    seed_langfuse
    seed_n8n
    seed_omi
    seed_authentik
    seed_grafana

    # Gateway and monitoring
    seed_traefik
    seed_prometheus
    seed_woodpecker
    seed_thanos

    # AI services
    seed_openhands
    seed_swe_agent
    seed_ollama
    seed_flowise

    # Business applications
    seed_plane
    seed_wikijs
    seed_superset
    seed_calcom
    seed_twenty
    seed_crater

    # Developer tools
    seed_coder
    seed_nango
    seed_qdrant
    seed_token_infinity
    seed_mlflow

    # Security and ops
    seed_crowdsec
    seed_portainer
    seed_uptime_kuma
    seed_coolify
    seed_keycloak

    # Communication and engagement
    seed_glitchtip
    seed_listmonk
    seed_chatwoot
    seed_pact_broker
    seed_formbricks
    seed_tolgee

    output_summary

    log_ok "Secret seeding complete"
}

main "$@"
