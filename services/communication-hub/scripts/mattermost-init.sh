#!/usr/bin/env bash
###############################################################################
# SYSTEM 10 — COMMUNICATION HUB: Mattermost Initialization
# Omni Quantum Elite AI Coding System — Communication & Workflow Layer
#
# Configures team, channels, bots, webhooks, and OAuth via mmctl + REST API.
# All credentials stored in / read from Vault KV v2.
###############################################################################
set -euo pipefail

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
MM_URL="${MATTERMOST_URL:-http://omni-mattermost:8065}"
MM_ADMIN_USER="${MATTERMOST_ADMIN_USER:-omni-admin}"
MM_ADMIN_PASS="${MATTERMOST_ADMIN_PASS}"
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN}"

TEAM_NAME="omni-quantum"
TEAM_DISPLAY="Omni Quantum Elite"
LOG_PREFIX="[mattermost-init]"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_info()  { echo "{\"level\":\"info\",\"service\":\"mattermost-init\",\"system\":\"10\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}"; }
log_error() { echo "{\"level\":\"error\",\"service\":\"mattermost-init\",\"system\":\"10\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}" >&2; }
log_warn()  { echo "{\"level\":\"warn\",\"service\":\"mattermost-init\",\"system\":\"10\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}"; }

mm_api() {
    local method="$1" path="$2"; shift 2
    curl -sf -X "$method" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" \
        -H "Content-Type: application/json" \
        "${MM_URL}/api/v4${path}" "$@"
}

vault_kv_put() {
    local path="$1" payload="$2"
    curl -sf -X POST \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"data\":${payload}}" \
        "${VAULT_ADDR}/v1/secret/data/${path}" >/dev/null
}

vault_kv_get() {
    local path="$1"
    curl -sf \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/secret/data/${path}" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)['data']['data']))"
}

# ---------------------------------------------------------------------------
# Wait for Mattermost
# ---------------------------------------------------------------------------
wait_for_mattermost() {
    log_info "Waiting for Mattermost at ${MM_URL} ..."
    local retries=0 max_retries=60
    while [ "$retries" -lt "$max_retries" ]; do
        if curl -sf "${MM_URL}/api/v4/system/ping" | grep -q '"status":"OK"'; then
            log_info "Mattermost is healthy"
            return 0
        fi
        retries=$((retries + 1))
        sleep 5
    done
    log_error "Mattermost did not become healthy after $((max_retries * 5))s"
    exit 1
}

# ---------------------------------------------------------------------------
# Authenticate
# ---------------------------------------------------------------------------
authenticate() {
    log_info "Authenticating as ${MM_ADMIN_USER} ..."
    AUTH_TOKEN=$(curl -sf -X POST \
        -H "Content-Type: application/json" \
        -d "{\"login_id\":\"${MM_ADMIN_USER}\",\"password\":\"${MM_ADMIN_PASS}\"}" \
        "${MM_URL}/api/v4/users/login" \
        -D - -o /dev/null 2>/dev/null | grep -i '^Token:' | tr -d '[:space:]' | cut -d: -f2)

    if [ -z "${AUTH_TOKEN:-}" ]; then
        log_error "Authentication failed"
        exit 1
    fi
    log_info "Authenticated successfully"
}

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
create_team() {
    log_info "Creating team: ${TEAM_NAME} ..."
    local existing
    existing=$(mm_api GET "/teams/name/${TEAM_NAME}" 2>/dev/null || echo "")
    if echo "$existing" | python3 -c "import sys,json; json.load(sys.stdin)['id']" 2>/dev/null; then
        TEAM_ID=$(echo "$existing" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
        log_info "Team already exists: ${TEAM_ID}"
    else
        local resp
        resp=$(mm_api POST "/teams" -d "{
            \"name\": \"${TEAM_NAME}\",
            \"display_name\": \"${TEAM_DISPLAY}\",
            \"type\": \"I\"
        }")
        TEAM_ID=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
        log_info "Team created: ${TEAM_ID}"
    fi
}

# ---------------------------------------------------------------------------
# Create Channels
# ---------------------------------------------------------------------------
declare -A CHANNEL_IDS

create_channel() {
    local name="$1" purpose="$2" header="${3:-}"
    log_info "Creating channel: #${name} ..."
    local existing
    existing=$(mm_api GET "/teams/${TEAM_ID}/channels/name/${name}" 2>/dev/null || echo "")
    if echo "$existing" | python3 -c "import sys,json; json.load(sys.stdin)['id']" 2>/dev/null; then
        CHANNEL_IDS[$name]=$(echo "$existing" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
        log_info "Channel #${name} already exists: ${CHANNEL_IDS[$name]}"
    else
        local resp
        resp=$(mm_api POST "/channels" -d "{
            \"team_id\": \"${TEAM_ID}\",
            \"name\": \"${name}\",
            \"display_name\": \"${name}\",
            \"type\": \"O\",
            \"purpose\": \"${purpose}\",
            \"header\": \"${header}\"
        }")
        CHANNEL_IDS[$name]=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
        log_info "Channel #${name} created: ${CHANNEL_IDS[$name]}"
    fi
}

create_all_channels() {
    create_channel "omni-alerts"      "Critical system alerts from Alertmanager, CrowdSec, Uptime Kuma, Backup Fortress, Secret Rotation"
    create_channel "omni-builds"      "CI/CD pipeline status from Woodpecker, Code Scorer, Gate Engine"
    create_channel "omni-reviews"     "Code review notifications and quality scores"
    create_channel "omni-deployments" "Deploy status and approval requests from Coolify, Woodpecker, Orchestrator"
    create_channel "omni-financial"   "Invoice, payment, and budget alerts from financial microservices and Crater"
    create_channel "omni-knowledge"   "Knowledge base updates and staleness alerts"
    create_channel "omni-security"    "Security events, bans, and audit logs from CrowdSec, Vault, Authentik"
    create_channel "omni-general"     "Platform discussion and Orchestrator commands"
    create_channel "omni-incidents"   "Active incident management from Uptime Kuma and Prometheus"
    create_channel "omni-costs"       "LLM and infrastructure cost tracking from LiteLLM and Langfuse"
}

# ---------------------------------------------------------------------------
# Create Bot Accounts
# ---------------------------------------------------------------------------
declare -A BOT_TOKENS

create_bot() {
    local username="$1" display="$2" description="$3"
    log_info "Creating bot: ${username} ..."

    local existing
    existing=$(mm_api GET "/bots" 2>/dev/null | python3 -c "
import sys, json
bots = json.load(sys.stdin)
for b in bots:
    if b['username'] == '${username}':
        print(b['user_id'])
        break
" 2>/dev/null || echo "")

    local bot_user_id
    if [ -n "$existing" ]; then
        bot_user_id="$existing"
        log_info "Bot ${username} already exists: ${bot_user_id}"
    else
        local resp
        resp=$(mm_api POST "/bots" -d "{
            \"username\": \"${username}\",
            \"display_name\": \"${display}\",
            \"description\": \"${description}\"
        }")
        bot_user_id=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['user_id'])")
        log_info "Bot ${username} created: ${bot_user_id}"
    fi

    # Generate access token
    local token_resp
    token_resp=$(mm_api POST "/users/${bot_user_id}/tokens" -d "{
        \"description\": \"Omni Quantum ${display} token\"
    }")
    local token
    token=$(echo "$token_resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
    BOT_TOKENS[$username]="$token"

    # Store token in Vault
    vault_kv_put "mattermost/bots/${username}" "{\"token\":\"${token}\",\"user_id\":\"${bot_user_id}\"}"
    log_info "Bot ${username} token stored in Vault"
}

create_all_bots() {
    create_bot "alertbot" "Alert Bot 🚨"   "Posts critical alerts to #alerts, #security, #incidents"
    create_bot "cicdbot"  "CI/CD Bot 🔨"   "Posts build and deploy status to #builds, #deployments"
    create_bot "aibot"    "AI Bot 🤖"      "Posts review scores and knowledge updates to #reviews, #knowledge"
    create_bot "finbot"   "Finance Bot 💰"  "Posts financial and cost alerts to #financial, #costs"
    create_bot "omnibot"  "Omni Bot ⚛️"    "General platform notifications to #general"
}

# ---------------------------------------------------------------------------
# Add Bots to Channels
# ---------------------------------------------------------------------------
add_bot_to_channel() {
    local bot_username="$1" channel_name="$2"
    local bot_user_id
    bot_user_id=$(mm_api GET "/bots" | python3 -c "
import sys, json
for b in json.load(sys.stdin):
    if b['username'] == '${bot_username}':
        print(b['user_id']); break
" 2>/dev/null || echo "")
    if [ -n "$bot_user_id" ]; then
        mm_api POST "/channels/${CHANNEL_IDS[$channel_name]}/members" \
            -d "{\"user_id\":\"${bot_user_id}\"}" >/dev/null 2>&1 || true
    fi
}

assign_bots_to_channels() {
    log_info "Assigning bots to channels ..."
    add_bot_to_channel "alertbot" "omni-alerts"
    add_bot_to_channel "alertbot" "omni-security"
    add_bot_to_channel "alertbot" "omni-incidents"
    add_bot_to_channel "cicdbot"  "omni-builds"
    add_bot_to_channel "cicdbot"  "omni-deployments"
    add_bot_to_channel "aibot"    "omni-reviews"
    add_bot_to_channel "aibot"    "omni-knowledge"
    add_bot_to_channel "finbot"   "omni-financial"
    add_bot_to_channel "finbot"   "omni-costs"
    add_bot_to_channel "omnibot"  "omni-general"
}

# ---------------------------------------------------------------------------
# Create Incoming Webhooks
# ---------------------------------------------------------------------------
create_incoming_webhook() {
    local channel_name="$1" display_name="$2"
    log_info "Creating incoming webhook for #${channel_name} ..."
    local resp
    resp=$(mm_api POST "/hooks/incoming" -d "{
        \"channel_id\": \"${CHANNEL_IDS[$channel_name]}\",
        \"display_name\": \"${display_name}\",
        \"description\": \"Omni Quantum webhook for #${channel_name}\"
    }")
    local hook_id hook_url
    hook_id=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    hook_url="${MM_URL}/hooks/${hook_id}"

    vault_kv_put "mattermost/webhooks/${channel_name}" "{\"url\":\"${hook_url}\",\"id\":\"${hook_id}\"}"
    log_info "Webhook for #${channel_name} stored in Vault: ${hook_id}"
}

create_all_webhooks() {
    create_incoming_webhook "omni-alerts"      "Alerts Webhook"
    create_incoming_webhook "omni-builds"      "Builds Webhook"
    create_incoming_webhook "omni-reviews"     "Reviews Webhook"
    create_incoming_webhook "omni-deployments" "Deployments Webhook"
    create_incoming_webhook "omni-financial"   "Financial Webhook"
    create_incoming_webhook "omni-knowledge"   "Knowledge Webhook"
    create_incoming_webhook "omni-security"    "Security Webhook"
    create_incoming_webhook "omni-general"     "General Webhook"
    create_incoming_webhook "omni-incidents"   "Incidents Webhook"
    create_incoming_webhook "omni-costs"       "Costs Webhook"
}

# ---------------------------------------------------------------------------
# Configure OAuth2 with Authentik
# ---------------------------------------------------------------------------
configure_oauth() {
    log_info "Configuring OAuth2 with Authentik ..."

    local oauth_creds
    oauth_creds=$(vault_kv_get "authentik/oauth/mattermost" 2>/dev/null || echo "")
    if [ -z "$oauth_creds" ]; then
        log_warn "No Authentik OAuth credentials found in Vault — skipping OAuth setup"
        return 0
    fi

    local client_id client_secret
    client_id=$(echo "$oauth_creds" | python3 -c "import sys,json; print(json.load(sys.stdin)['client_id'])")
    client_secret=$(echo "$oauth_creds" | python3 -c "import sys,json; print(json.load(sys.stdin)['client_secret'])")

    # Configure Mattermost OpenID Connect
    mm_api PUT "/config" -d "{
        \"GitLabSettings\": {
            \"Enable\": false
        },
        \"OpenIdSettings\": {
            \"Enable\": true,
            \"Secret\": \"${client_secret}\",
            \"Id\": \"${client_id}\",
            \"DiscoveryEndpoint\": \"https://auth.omni-quantum.internal/application/o/mattermost/.well-known/openid-configuration\",
            \"ButtonText\": \"Sign in with Omni Quantum SSO\",
            \"ButtonColor\": \"#6366f1\"
        }
    }" >/dev/null

    log_info "OAuth2 configured with Authentik"
}

# ---------------------------------------------------------------------------
# Configure notification preferences
# ---------------------------------------------------------------------------
configure_notification_defaults() {
    log_info "Configuring notification defaults ..."
    mm_api PUT "/config" -d "{
        \"TeamSettings\": {
            \"SiteName\": \"Omni Quantum Elite\",
            \"MaxChannelsPerTeam\": 500,
            \"EnableOpenServer\": false,
            \"RestrictDirectMessage\": \"team\"
        },
        \"ServiceSettings\": {
            \"EnableIncomingWebhooks\": true,
            \"EnableOutgoingWebhooks\": true,
            \"EnableBotAccountCreation\": true,
            \"EnableOAuthServiceProvider\": true,
            \"EnablePostUsernameOverride\": true,
            \"EnablePostIconOverride\": true
        },
        \"NotificationLogSettings\": {
            \"SMTPServerTimeout\": 10
        }
    }" >/dev/null 2>&1 || log_warn "Some config settings may not have applied"
    log_info "Notification defaults configured"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    log_info "=== Mattermost Communication Hub Init ==="
    log_info "System 10 — Communication Hub"

    wait_for_mattermost
    authenticate
    create_team
    create_all_channels
    create_all_bots
    assign_bots_to_channels
    create_all_webhooks
    configure_notification_defaults
    configure_oauth

    log_info "=== Mattermost init complete ==="
    log_info "Team: ${TEAM_NAME} (${TEAM_ID})"
    log_info "Channels: ${#CHANNEL_IDS[@]} created/verified"
    log_info "Bots: ${#BOT_TOKENS[@]} created with tokens in Vault"
    log_info "Webhooks: stored in Vault at secret/data/mattermost/webhooks/*"
}

main "$@"
