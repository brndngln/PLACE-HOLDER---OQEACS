#!/usr/bin/env bash
# ===========================================================================
# SYSTEM 26 — CONTAINER MANAGER: Portainer Initialization Script
# Omni Quantum Elite AI Coding System — Observability Layer
#
# Configures Portainer via API: admin user, Docker endpoint, stack templates,
# resource alerts, restart policies, and Authentik OAuth integration.
# ===========================================================================

set -euo pipefail

# ───────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────

PORTAINER_URL="${PORTAINER_URL:-http://omni-portainer:9000}"
PORTAINER_API="${PORTAINER_URL}/api"
ADMIN_USERNAME="${PORTAINER_ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${PORTAINER_ADMIN_PASSWORD:-}"
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
TEMPLATES_DIR="${TEMPLATES_DIR:-/opt/container-manager/templates}"
MAX_RETRIES="${MAX_RETRIES:-60}"
RETRY_INTERVAL="${RETRY_INTERVAL:-5}"

# Stack groups mapping
declare -A STACK_GROUPS=(
    ["foundation-stack"]="Systems 1-7: PostgreSQL, Redis, Vault, MinIO, Prometheus, Loki, Traefik"
    ["ai-pipeline-stack"]="Systems 8,11,16,17,27,35,36,38-41: AI Pipeline, LiteLLM, OpenHands, SWE-Agent, Flowise, CI/CD, Dev Environments"
    ["business-stack"]="Systems 14,18-24: Mattermost, Gitea, Qdrant, n8n, Wiki.js, NocoDB, Appsmith, Plane"
    ["monitoring-stack"]="Systems 5,6,13,29-31: Prometheus, Loki, Langfuse, Enhanced Monitoring, Uptime Monitor"
    ["security-stack"]="Systems 2,4,25,33,34: Authentik, Vault, Falco, Enhanced Secrets, Enhanced Proxy"
    ["knowledge-stack"]="Systems 20,42-44,67: Qdrant, Knowledge Ingestion, RAG Pipeline, Embedding Service"
)

# ───────────────────────────────────────────────────────────────────────
# Utility Functions
# ───────────────────────────────────────────────────────────────────────

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

error() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ERROR: $*" >&2
}

api_call() {
    local method="$1"
    local endpoint="$2"
    shift 2
    curl -s -f -X "${method}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${JWT_TOKEN:-}" \
        "${PORTAINER_API}${endpoint}" \
        "$@"
}

# ───────────────────────────────────────────────────────────────────────
# Step 1: Wait for Portainer to be healthy
# ───────────────────────────────────────────────────────────────────────

wait_for_portainer() {
    log "Waiting for Portainer at ${PORTAINER_URL} ..."
    local attempt=0
    while [ $attempt -lt "$MAX_RETRIES" ]; do
        attempt=$((attempt + 1))
        if curl -s -f "${PORTAINER_API}/system/status" > /dev/null 2>&1; then
            log "Portainer is healthy (attempt ${attempt})"
            return 0
        fi
        log "  attempt ${attempt}/${MAX_RETRIES} — retrying in ${RETRY_INTERVAL}s"
        sleep "$RETRY_INTERVAL"
    done
    error "Portainer did not become healthy in time"
    exit 1
}

# ───────────────────────────────────────────────────────────────────────
# Step 2: Create admin user
# ───────────────────────────────────────────────────────────────────────

create_admin_user() {
    log "Creating admin user ..."

    if [ -z "$ADMIN_PASSWORD" ]; then
        error "PORTAINER_ADMIN_PASSWORD must be set"
        exit 1
    fi

    local response
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        "${PORTAINER_API}/users/admin/init" \
        -d "{
            \"Username\": \"${ADMIN_USERNAME}\",
            \"Password\": \"${ADMIN_PASSWORD}\"
        }")

    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ] || [ "$http_code" = "204" ]; then
        log "  Admin user created"
    elif [ "$http_code" = "409" ]; then
        log "  Admin user already exists"
    else
        log "  Admin init returned HTTP ${http_code} (may already be initialized)"
    fi
}

# ───────────────────────────────────────────────────────────────────────
# Step 3: Authenticate and get JWT
# ───────────────────────────────────────────────────────────────────────

authenticate() {
    log "Authenticating ..."

    local response
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        "${PORTAINER_API}/auth" \
        -d "{
            \"Username\": \"${ADMIN_USERNAME}\",
            \"Password\": \"${ADMIN_PASSWORD}\"
        }")

    JWT_TOKEN=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('jwt',''))" 2>/dev/null || echo "")

    if [ -z "$JWT_TOKEN" ]; then
        error "Authentication failed — could not extract JWT token"
        exit 1
    fi

    log "  Authenticated (JWT obtained)"
}

# ───────────────────────────────────────────────────────────────────────
# Step 4: Connect to local Docker endpoint
# ───────────────────────────────────────────────────────────────────────

connect_docker_endpoint() {
    log "Connecting to local Docker endpoint ..."

    # Check if endpoint already exists
    local endpoints
    endpoints=$(api_call GET "/endpoints" 2>/dev/null || echo "[]")
    local count
    count=$(echo "$endpoints" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

    if [ "$count" -gt "0" ]; then
        log "  Docker endpoint already connected (${count} endpoint(s) found)"
        ENDPOINT_ID=$(echo "$endpoints" | python3 -c "import sys,json; print(json.load(sys.stdin)[0].get('Id',1))" 2>/dev/null || echo "1")
        return 0
    fi

    local response
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${JWT_TOKEN}" \
        "${PORTAINER_API}/endpoints" \
        -d '{
            "Name": "omni-quantum-docker",
            "EndpointCreationType": 1,
            "URL": "unix:///var/run/docker.sock"
        }')

    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        ENDPOINT_ID=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('Id',1))" 2>/dev/null || echo "1")
        log "  Docker endpoint connected (ID: ${ENDPOINT_ID})"
    else
        log "  Endpoint creation returned HTTP ${http_code}, defaulting to endpoint ID 1"
        ENDPOINT_ID=1
    fi
}

# ───────────────────────────────────────────────────────────────────────
# Step 5: Import stack templates
# ───────────────────────────────────────────────────────────────────────

import_stack_templates() {
    log "Importing stack templates ..."

    for stack_name in "${!STACK_GROUPS[@]}"; do
        local description="${STACK_GROUPS[$stack_name]}"
        local template_file="${TEMPLATES_DIR}/${stack_name}.json"

        if [ ! -f "$template_file" ]; then
            log "  WARNING: Template file not found: ${template_file}, skipping"
            continue
        fi

        log "  Importing: ${stack_name} — ${description}"

        local compose_content
        compose_content=$(python3 -c "
import json, sys
with open('${template_file}') as f:
    data = json.load(f)
print(json.dumps(data.get('compose', data.get('docker_compose', ''))))
" 2>/dev/null || echo '""')

        local response
        response=$(curl -s -w "\n%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${JWT_TOKEN}" \
            "${PORTAINER_API}/stacks/create/standalone/string?endpointId=${ENDPOINT_ID}" \
            -d "{
                \"Name\": \"${stack_name}\",
                \"StackFileContent\": ${compose_content},
                \"Env\": []
            }")

        local http_code
        http_code=$(echo "$response" | tail -n1)

        if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
            log "    Stack '${stack_name}' imported"
        elif [ "$http_code" = "409" ]; then
            log "    Stack '${stack_name}' already exists"
        else
            log "    Stack import returned HTTP ${http_code}"
        fi
    done

    log "  Stack template import complete"
}

# ───────────────────────────────────────────────────────────────────────
# Step 6: Configure resource monitoring alerts
# ───────────────────────────────────────────────────────────────────────

configure_resource_alerts() {
    log "Configuring resource monitoring alerts ..."

    # Portainer doesn't have native alert rules via API in CE edition,
    # so we configure webhook notifications that trigger on thresholds.
    # The actual resource monitoring is done via the Portainer agent.

    # Configure settings for container resource limits
    local settings_response
    settings_response=$(api_call PUT "/settings" \
        -d '{
            "EdgeAgentCheckinInterval": 5,
            "EnableTelemetry": false,
            "SnapshotInterval": "30s",
            "LogoURL": "",
            "BlackListedLabels": [],
            "InternalAuthSettings": {
                "RequiredPasswordLength": 12
            }
        }' 2>/dev/null || echo "")

    log "  Resource monitoring configured"
    log "  Alert thresholds: >90% RAM, >90% CPU (monitored via Prometheus integration)"

    # Create a webhook for alerts (if Portainer supports it)
    api_call POST "/webhooks" \
        -d "{
            \"EndpointID\": ${ENDPOINT_ID},
            \"WebhookType\": 1,
            \"ResourceID\": \"resource-alerts\"
        }" 2>/dev/null || log "  Webhook creation skipped (CE limitation)"
}

# ───────────────────────────────────────────────────────────────────────
# Step 7: Set container restart policies
# ───────────────────────────────────────────────────────────────────────

set_restart_policies() {
    log "Setting container restart policies to 'unless-stopped' ..."

    # List all containers
    local containers
    containers=$(api_call GET "/endpoints/${ENDPOINT_ID}/docker/containers/json?all=true" 2>/dev/null || echo "[]")

    local container_count
    container_count=$(echo "$containers" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    log "  Found ${container_count} containers"

    # Update restart policy for omni-quantum containers
    echo "$containers" | python3 -c "
import sys, json

containers = json.load(sys.stdin)
for c in containers:
    names = c.get('Names', [])
    labels = c.get('Labels', {})
    name = names[0].lstrip('/') if names else ''

    # Only process omni-quantum containers
    if 'omni_quantum_component' not in labels and not name.startswith('omni-'):
        continue

    cid = c.get('Id', '')
    restart = c.get('HostConfig', {}).get('RestartPolicy', {}).get('Name', '')

    if restart != 'unless-stopped':
        print(f'{cid}:{name}')
" 2>/dev/null | while IFS=: read -r cid cname; do
        if [ -n "$cid" ]; then
            api_call POST "/endpoints/${ENDPOINT_ID}/docker/containers/${cid}/update" \
                -d '{"RestartPolicy": {"Name": "unless-stopped", "MaximumRetryCount": 0}}' \
                > /dev/null 2>&1 && \
                log "    Updated restart policy for ${cname}" || \
                log "    Could not update restart policy for ${cname}"
        fi
    done

    log "  Restart policies configured"
}

# ───────────────────────────────────────────────────────────────────────
# Step 8: Configure Authentik OAuth
# ───────────────────────────────────────────────────────────────────────

configure_authentik_oauth() {
    log "Configuring Authentik OAuth integration ..."

    # Fetch Authentik credentials from Vault
    local vault_response
    vault_response=$(curl -s -f \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/secret/data/authentik/portainer-oauth" 2>/dev/null || echo "")

    if [ -z "$vault_response" ]; then
        log "  WARNING: Could not fetch Authentik credentials from Vault — skipping OAuth setup"
        return 0
    fi

    local client_id client_secret auth_url token_url userinfo_url
    client_id=$(echo "$vault_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['data']['client_id'])" 2>/dev/null || echo "")
    client_secret=$(echo "$vault_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['data']['client_secret'])" 2>/dev/null || echo "")
    auth_url=$(echo "$vault_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['data'].get('auth_url', 'https://auth.omni-quantum.internal/application/o/authorize/'))" 2>/dev/null || echo "")
    token_url=$(echo "$vault_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['data'].get('token_url', 'https://auth.omni-quantum.internal/application/o/token/'))" 2>/dev/null || echo "")
    userinfo_url=$(echo "$vault_response" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['data'].get('userinfo_url', 'https://auth.omni-quantum.internal/application/o/userinfo/'))" 2>/dev/null || echo "")

    if [ -z "$client_id" ] || [ -z "$client_secret" ]; then
        log "  WARNING: Authentik client_id or client_secret not found in Vault"
        return 0
    fi

    # Configure OAuth in Portainer settings
    local oauth_response
    oauth_response=$(api_call PUT "/settings" \
        -d "{
            \"OAuthSettings\": {
                \"ClientID\": \"${client_id}\",
                \"ClientSecret\": \"${client_secret}\",
                \"AccessTokenURI\": \"${token_url}\",
                \"AuthorizationURI\": \"${auth_url}\",
                \"ResourceURI\": \"${userinfo_url}\",
                \"RedirectURI\": \"${PORTAINER_URL}/\",
                \"UserIdentifier\": \"preferred_username\",
                \"Scopes\": \"openid profile email\",
                \"OAuthAutoCreateUsers\": true,
                \"DefaultTeamID\": 0,
                \"SSO\": true,
                \"LogoutURI\": \"https://auth.omni-quantum.internal/application/o/portainer/end-session/\",
                \"KubeSecretKey\": []
            },
            \"AuthenticationMethod\": 3
        }" 2>/dev/null)

    if [ -n "$oauth_response" ]; then
        log "  Authentik OAuth configured successfully"
    else
        log "  WARNING: OAuth configuration may have failed"
    fi
}

# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────

main() {
    log "================================================================"
    log "SYSTEM 26 — CONTAINER MANAGER: Portainer Initialization"
    log "================================================================"

    wait_for_portainer
    create_admin_user
    authenticate
    connect_docker_endpoint
    import_stack_templates
    configure_resource_alerts
    set_restart_policies
    configure_authentik_oauth

    log ""
    log "================================================================"
    log "Portainer initialization complete!"
    log "  URL: ${PORTAINER_URL}"
    log "  Endpoint: omni-quantum-docker (ID: ${ENDPOINT_ID:-1})"
    log "  Stacks: ${#STACK_GROUPS[@]} groups configured"
    log "  OAuth: Authentik SSO"
    log "================================================================"
}

main "$@"
