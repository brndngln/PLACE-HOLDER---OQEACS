#!/usr/bin/env bash
# ===========================================================================
# SYSTEM 4 — SECURITY NEXUS: Service OAuth Config Generator
# Omni Quantum Elite AI Coding System — Security & Identity Layer
#
# After authentik-init.py runs, this script reads OAuth credentials from
# Vault and generates environment variable snippets for each service.
# Output: per-service .env fragments and a consolidated oauth.env file.
# ===========================================================================

set -euo pipefail

# ───────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────

VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
AUTHENTIK_URL="${AUTHENTIK_URL:-http://omni-authentik:9000}"
OUTPUT_DIR="${OUTPUT_DIR:-/opt/omni-quantum/oauth-configs}"
CONSOLIDATED_ENV="${CONSOLIDATED_ENV:-/opt/omni-quantum/.env.oauth}"

# All services with OAuth configured by authentik-init.py
SERVICES=(
    gitea
    grafana
    mattermost
    portainer
    plane
    superset
    wikijs
    langfuse
    n8n
    coolify
    woodpecker
    orchestrator
)

# ───────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

error() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ERROR: $*" >&2
}

vault_read() {
    local path="$1"
    curl -sf \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/secret/data/${path}" 2>/dev/null
}

extract_field() {
    local json="$1"
    local field="$2"
    echo "$json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('data', {}).get('data', {}).get('${field}', ''))
" 2>/dev/null
}

to_upper_snake() {
    echo "$1" | tr '[:lower:]-' '[:upper:]_'
}

# ───────────────────────────────────────────────────────────────────────
# Validation
# ───────────────────────────────────────────────────────────────────────

if [ -z "$VAULT_TOKEN" ]; then
    error "VAULT_TOKEN must be set"
    exit 1
fi

# Verify Vault connectivity
if ! curl -sf -H "X-Vault-Token: ${VAULT_TOKEN}" "${VAULT_ADDR}/v1/sys/health" > /dev/null 2>&1; then
    error "Cannot connect to Vault at ${VAULT_ADDR}"
    exit 1
fi

# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────

log "================================================================"
log "SYSTEM 4 — Generating OAuth Service Configurations"
log "================================================================"

mkdir -p "$OUTPUT_DIR"

# Clear consolidated env file
: > "$CONSOLIDATED_ENV"
echo "# ================================================================" >> "$CONSOLIDATED_ENV"
echo "# Omni Quantum Elite — OAuth Environment Variables" >> "$CONSOLIDATED_ENV"
echo "# Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$CONSOLIDATED_ENV"
echo "# Source: Vault secret/data/authentik/clients/{service}" >> "$CONSOLIDATED_ENV"
echo "# ================================================================" >> "$CONSOLIDATED_ENV"
echo "" >> "$CONSOLIDATED_ENV"

success_count=0
fail_count=0

for service in "${SERVICES[@]}"; do
    log "Processing: ${service} ..."
    SERVICE_UPPER=$(to_upper_snake "$service")

    # Read credentials from Vault
    vault_response=$(vault_read "authentik/clients/${service}")

    if [ -z "$vault_response" ]; then
        error "  No Vault data for ${service} — skipping"
        fail_count=$((fail_count + 1))
        continue
    fi

    client_id=$(extract_field "$vault_response" "client_id")
    client_secret=$(extract_field "$vault_response" "client_secret")
    issuer_url=$(extract_field "$vault_response" "issuer_url")
    authorize_url=$(extract_field "$vault_response" "authorize_url")
    token_url=$(extract_field "$vault_response" "token_url")
    userinfo_url=$(extract_field "$vault_response" "userinfo_url")
    jwks_url=$(extract_field "$vault_response" "jwks_url")
    end_session_url=$(extract_field "$vault_response" "end_session_url")

    if [ -z "$client_id" ] || [ -z "$client_secret" ]; then
        error "  Missing client_id or client_secret for ${service}"
        fail_count=$((fail_count + 1))
        continue
    fi

    # ── Per-service .env fragment ──
    service_env="${OUTPUT_DIR}/${service}.env"
    cat > "$service_env" <<ENVEOF
# OAuth2/OIDC configuration for ${service}
# Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')
${SERVICE_UPPER}_OAUTH_CLIENT_ID=${client_id}
${SERVICE_UPPER}_OAUTH_CLIENT_SECRET=${client_secret}
${SERVICE_UPPER}_OAUTH_ISSUER_URL=${issuer_url}
${SERVICE_UPPER}_OAUTH_AUTHORIZE_URL=${authorize_url}
${SERVICE_UPPER}_OAUTH_TOKEN_URL=${token_url}
${SERVICE_UPPER}_OAUTH_USERINFO_URL=${userinfo_url}
${SERVICE_UPPER}_OAUTH_JWKS_URL=${jwks_url}
${SERVICE_UPPER}_OAUTH_END_SESSION_URL=${end_session_url}
ENVEOF

    # ── Service-specific env vars (native config names) ──
    case "$service" in
        gitea)
            cat >> "$service_env" <<ENVEOF
# Gitea-native OAuth config
GITEA__oauth2__ENABLED=true
GITEA__oauth2__PROVIDER=openidConnect
GITEA__oauth2__OPENID_CONNECT_AUTO_DISCOVERY_URL=${issuer_url}.well-known/openid-configuration
ENVEOF
            ;;
        grafana)
            cat >> "$service_env" <<ENVEOF
# Grafana-native OAuth config
GF_AUTH_GENERIC_OAUTH_ENABLED=true
GF_AUTH_GENERIC_OAUTH_NAME=Authentik
GF_AUTH_GENERIC_OAUTH_CLIENT_ID=${client_id}
GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET=${client_secret}
GF_AUTH_GENERIC_OAUTH_SCOPES=openid profile email
GF_AUTH_GENERIC_OAUTH_AUTH_URL=${authorize_url}
GF_AUTH_GENERIC_OAUTH_TOKEN_URL=${token_url}
GF_AUTH_GENERIC_OAUTH_API_URL=${userinfo_url}
GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH=contains(groups[*], 'omni-admins') && 'Admin' || contains(groups[*], 'omni-operators') && 'Editor' || 'Viewer'
GF_AUTH_GENERIC_OAUTH_ALLOW_SIGN_UP=true
GF_AUTH_SIGNOUT_REDIRECT_URL=${end_session_url}
ENVEOF
            ;;
        mattermost)
            cat >> "$service_env" <<ENVEOF
# Mattermost-native OAuth config (GitLab-compatible mode)
MM_GITLABSETTINGS_ENABLE=true
MM_GITLABSETTINGS_ID=${client_id}
MM_GITLABSETTINGS_SECRET=${client_secret}
MM_GITLABSETTINGS_AUTHENDPOINT=${authorize_url}
MM_GITLABSETTINGS_TOKENENDPOINT=${token_url}
MM_GITLABSETTINGS_USERAPIENDPOINT=${userinfo_url}
ENVEOF
            ;;
        portainer)
            cat >> "$service_env" <<ENVEOF
# Portainer OAuth config (applied via API, not env vars)
PORTAINER_OAUTH_CLIENT_ID=${client_id}
PORTAINER_OAUTH_CLIENT_SECRET=${client_secret}
PORTAINER_OAUTH_AUTH_URL=${authorize_url}
PORTAINER_OAUTH_TOKEN_URL=${token_url}
PORTAINER_OAUTH_RESOURCE_URL=${userinfo_url}
PORTAINER_OAUTH_REDIRECT_URL=http://omni-portainer:9000
PORTAINER_OAUTH_USER_IDENTIFIER=preferred_username
PORTAINER_OAUTH_SCOPES=openid profile email
ENVEOF
            ;;
        wikijs)
            cat >> "$service_env" <<ENVEOF
# Wiki.js strategy config (applied via admin UI or GraphQL)
WIKIJS_OAUTH_CLIENT_ID=${client_id}
WIKIJS_OAUTH_CLIENT_SECRET=${client_secret}
WIKIJS_OAUTH_AUTHORIZATION_URL=${authorize_url}
WIKIJS_OAUTH_TOKEN_URL=${token_url}
WIKIJS_OAUTH_USERINFO_URL=${userinfo_url}
ENVEOF
            ;;
        langfuse)
            cat >> "$service_env" <<ENVEOF
# Langfuse custom OIDC config
AUTH_CUSTOM_CLIENT_ID=${client_id}
AUTH_CUSTOM_CLIENT_SECRET=${client_secret}
AUTH_CUSTOM_ISSUER=${issuer_url}
AUTH_CUSTOM_NAME=Authentik
ENVEOF
            ;;
        n8n)
            cat >> "$service_env" <<ENVEOF
# n8n external auth config
N8N_AUTH_OIDC_CLIENT_ID=${client_id}
N8N_AUTH_OIDC_CLIENT_SECRET=${client_secret}
N8N_AUTH_OIDC_ISSUER=${issuer_url}
ENVEOF
            ;;
        woodpecker)
            cat >> "$service_env" <<ENVEOF
# Woodpecker CI OAuth config
WOODPECKER_GITHUB=false
WOODPECKER_GITEA=false
WOODPECKER_OAUTH_CLIENT_ID=${client_id}
WOODPECKER_OAUTH_CLIENT_SECRET=${client_secret}
WOODPECKER_OAUTH_AUTHORIZE=${authorize_url}
WOODPECKER_OAUTH_ACCESS_TOKEN=${token_url}
WOODPECKER_OAUTH_USERINFO=${userinfo_url}
ENVEOF
            ;;
    esac

    # ── Append to consolidated env ──
    {
        echo "# --- ${service} ---"
        echo "${SERVICE_UPPER}_OAUTH_CLIENT_ID=${client_id}"
        echo "${SERVICE_UPPER}_OAUTH_CLIENT_SECRET=${client_secret}"
        echo "${SERVICE_UPPER}_OAUTH_ISSUER_URL=${issuer_url}"
        echo ""
    } >> "$CONSOLIDATED_ENV"

    log "  Written: ${service_env}"
    success_count=$((success_count + 1))
done

# ───────────────────────────────────────────────────────────────────────
# Summary
# ───────────────────────────────────────────────────────────────────────

# Set restrictive permissions on all generated files
chmod 600 "$OUTPUT_DIR"/*.env 2>/dev/null || true
chmod 600 "$CONSOLIDATED_ENV" 2>/dev/null || true

log ""
log "================================================================"
log "OAuth configuration generation complete!"
log "  Per-service configs: ${OUTPUT_DIR}/"
log "  Consolidated file:   ${CONSOLIDATED_ENV}"
log "  Successful: ${success_count}/${#SERVICES[@]}"
if [ "$fail_count" -gt 0 ]; then
    log "  Failed: ${fail_count} (check Vault paths)"
fi
log "================================================================"
