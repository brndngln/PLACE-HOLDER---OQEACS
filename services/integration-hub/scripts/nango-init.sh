#!/usr/bin/env bash
###############################################################################
# SYSTEM 15 — INTEGRATION HUB: Nango Initialization
# Omni Quantum Elite AI Coding System — Communication & Workflow Layer
#
# Configures Nango integrations: GitHub, Stripe, Google Calendar, Google Drive.
# Credentials loaded from Vault KV v2, webhook relay to n8n.
###############################################################################
set -euo pipefail

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
NANGO_URL="${NANGO_URL:-http://omni-nango:3003}"
NANGO_SECRET="${NANGO_SECRET_KEY:-}"
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN}"
N8N_URL="${N8N_URL:-http://omni-n8n:5678}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_info()  { echo "{\"level\":\"info\",\"service\":\"nango-init\",\"system\":\"15\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}"; }
log_error() { echo "{\"level\":\"error\",\"service\":\"nango-init\",\"system\":\"15\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}" >&2; }
log_warn()  { echo "{\"level\":\"warn\",\"service\":\"nango-init\",\"system\":\"15\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}"; }

nango_api() {
    local method="$1" path="$2"; shift 2
    curl -sf -X "$method" \
        -H "Authorization: Bearer ${NANGO_SECRET}" \
        -H "Content-Type: application/json" \
        "${NANGO_URL}${path}" "$@"
}

vault_kv_get() {
    local path="$1"
    curl -sf \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/secret/data/${path}" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)['data']['data']))"
}

vault_kv_put() {
    local path="$1" payload="$2"
    curl -sf -X POST \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"data\":${payload}}" \
        "${VAULT_ADDR}/v1/secret/data/${path}" >/dev/null
}

# ---------------------------------------------------------------------------
# Wait for Nango
# ---------------------------------------------------------------------------
wait_for_nango() {
    log_info "Waiting for Nango at ${NANGO_URL} ..."
    local retries=0 max_retries=60
    while [ "$retries" -lt "$max_retries" ]; do
        if curl -sf "${NANGO_URL}/health" >/dev/null 2>&1; then
            log_info "Nango is healthy"
            return 0
        fi
        retries=$((retries + 1))
        sleep 5
    done
    log_error "Nango did not become healthy after $((max_retries * 5))s"
    exit 1
}

# ---------------------------------------------------------------------------
# Setup: GitHub Integration
# ---------------------------------------------------------------------------
setup_github() {
    log_info "Configuring GitHub integration ..."

    local creds
    creds=$(vault_kv_get "nango/github" 2>/dev/null || echo "")
    if [ -z "$creds" ]; then
        log_warn "No GitHub OAuth credentials in Vault at secret/data/nango/github — skipping"
        return 0
    fi

    local client_id client_secret
    client_id=$(echo "$creds" | python3 -c "import sys,json; print(json.load(sys.stdin)['client_id'])")
    client_secret=$(echo "$creds" | python3 -c "import sys,json; print(json.load(sys.stdin)['client_secret'])")

    # Create integration config
    nango_api PUT "/config" -d "{
        \"provider_config_key\": \"github\",
        \"provider\": \"github\",
        \"oauth_client_id\": \"${client_id}\",
        \"oauth_client_secret\": \"${client_secret}\",
        \"oauth_scopes\": \"repo,read:org,write:org\"
    }" || nango_api PATCH "/config" -d "{
        \"provider_config_key\": \"github\",
        \"provider\": \"github\",
        \"oauth_client_id\": \"${client_id}\",
        \"oauth_client_secret\": \"${client_secret}\",
        \"oauth_scopes\": \"repo,read:org,write:org\"
    }"

    # Configure webhook relay to n8n
    nango_api POST "/webhook/github" -d "{
        \"provider_config_key\": \"github\",
        \"url\": \"${N8N_URL}/webhook/github\",
        \"events\": [\"push\", \"release\", \"security_advisory\", \"star\"]
    }" 2>/dev/null || log_warn "Webhook relay config may already exist"

    # Verify with test API call
    local test_result
    test_result=$(nango_api GET "/connection/github" 2>/dev/null || echo "")
    if [ -n "$test_result" ]; then
        log_info "GitHub integration verified"
    else
        log_warn "GitHub integration created but no active connection yet"
    fi

    log_info "GitHub integration configured"
}

# ---------------------------------------------------------------------------
# Setup: Stripe Integration
# ---------------------------------------------------------------------------
setup_stripe() {
    log_info "Configuring Stripe integration ..."

    local creds
    creds=$(vault_kv_get "nango/stripe" 2>/dev/null || echo "")
    if [ -z "$creds" ]; then
        log_warn "No Stripe API key in Vault at secret/data/nango/stripe — skipping"
        return 0
    fi

    local api_key webhook_secret
    api_key=$(echo "$creds" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_key'])")
    webhook_secret=$(echo "$creds" | python3 -c "import sys,json; print(json.load(sys.stdin).get('webhook_secret',''))")

    nango_api PUT "/config" -d "{
        \"provider_config_key\": \"stripe\",
        \"provider\": \"stripe\",
        \"oauth_client_id\": \"${api_key}\",
        \"oauth_client_secret\": \"${api_key}\"
    }" || nango_api PATCH "/config" -d "{
        \"provider_config_key\": \"stripe\",
        \"provider\": \"stripe\",
        \"oauth_client_id\": \"${api_key}\",
        \"oauth_client_secret\": \"${api_key}\"
    }"

    # Webhook relay for payment events
    nango_api POST "/webhook/stripe" -d "{
        \"provider_config_key\": \"stripe\",
        \"url\": \"${N8N_URL}/webhook/stripe\",
        \"events\": [\"payment_intent.succeeded\", \"invoice.paid\", \"invoice.payment_failed\"]
    }" 2>/dev/null || log_warn "Stripe webhook relay may already exist"

    # Store webhook secret for signature verification
    if [ -n "$webhook_secret" ]; then
        vault_kv_put "nango/stripe/webhook" "{\"webhook_secret\":\"${webhook_secret}\"}"
    fi

    log_info "Stripe integration configured"
}

# ---------------------------------------------------------------------------
# Setup: Google Calendar Integration
# ---------------------------------------------------------------------------
setup_google_calendar() {
    log_info "Configuring Google Calendar integration ..."

    local creds
    creds=$(vault_kv_get "nango/google-calendar" 2>/dev/null || echo "")
    if [ -z "$creds" ]; then
        log_warn "No Google Calendar OAuth in Vault at secret/data/nango/google-calendar — skipping"
        return 0
    fi

    local client_id client_secret
    client_id=$(echo "$creds" | python3 -c "import sys,json; print(json.load(sys.stdin)['client_id'])")
    client_secret=$(echo "$creds" | python3 -c "import sys,json; print(json.load(sys.stdin)['client_secret'])")

    nango_api PUT "/config" -d "{
        \"provider_config_key\": \"google-calendar\",
        \"provider\": \"google\",
        \"oauth_client_id\": \"${client_id}\",
        \"oauth_client_secret\": \"${client_secret}\",
        \"oauth_scopes\": \"https://www.googleapis.com/auth/calendar.readonly,https://www.googleapis.com/auth/calendar.events\"
    }" || nango_api PATCH "/config" -d "{
        \"provider_config_key\": \"google-calendar\",
        \"provider\": \"google\",
        \"oauth_client_id\": \"${client_id}\",
        \"oauth_client_secret\": \"${client_secret}\",
        \"oauth_scopes\": \"https://www.googleapis.com/auth/calendar.readonly,https://www.googleapis.com/auth/calendar.events\"
    }"

    log_info "Google Calendar integration configured — syncing to Cal.com"
}

# ---------------------------------------------------------------------------
# Setup: Google Drive Integration
# ---------------------------------------------------------------------------
setup_google_drive() {
    log_info "Configuring Google Drive integration ..."

    local creds
    creds=$(vault_kv_get "nango/google-drive" 2>/dev/null || echo "")
    if [ -z "$creds" ]; then
        log_warn "No Google Drive OAuth in Vault at secret/data/nango/google-drive — skipping"
        return 0
    fi

    local client_id client_secret
    client_id=$(echo "$creds" | python3 -c "import sys,json; print(json.load(sys.stdin)['client_id'])")
    client_secret=$(echo "$creds" | python3 -c "import sys,json; print(json.load(sys.stdin)['client_secret'])")

    nango_api PUT "/config" -d "{
        \"provider_config_key\": \"google-drive\",
        \"provider\": \"google\",
        \"oauth_client_id\": \"${client_id}\",
        \"oauth_client_secret\": \"${client_secret}\",
        \"oauth_scopes\": \"https://www.googleapis.com/auth/drive.readonly\"
    }" || nango_api PATCH "/config" -d "{
        \"provider_config_key\": \"google-drive\",
        \"provider\": \"google\",
        \"oauth_client_id\": \"${client_id}\",
        \"oauth_client_secret\": \"${client_secret}\",
        \"oauth_scopes\": \"https://www.googleapis.com/auth/drive.readonly\"
    }"

    log_info "Google Drive integration configured — feeding Knowledge Ingestion"
}

# ---------------------------------------------------------------------------
# Verify all integrations
# ---------------------------------------------------------------------------
verify_integrations() {
    log_info "Verifying all integrations ..."
    local configs
    configs=$(nango_api GET "/config" 2>/dev/null || echo "[]")
    local count
    count=$(echo "$configs" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('configs',d) if isinstance(d,dict) else d))" 2>/dev/null || echo "0")
    log_info "Active integration configs: ${count}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    log_info "=== Nango Integration Hub Init ==="
    log_info "System 15 — Integration Hub"

    wait_for_nango
    setup_github
    setup_stripe
    setup_google_calendar
    setup_google_drive
    verify_integrations

    log_info "=== Nango init complete ==="
}

main "$@"
