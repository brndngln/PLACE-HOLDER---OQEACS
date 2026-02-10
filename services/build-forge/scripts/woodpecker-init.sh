#!/usr/bin/env bash
# =============================================================================
# System 35 — Build Forge: Woodpecker CI Initialization Script
# Omni Quantum Elite AI Coding System
#
# This script performs first-time setup for the Woodpecker CI system:
#   1. Waits for dependent services to become healthy
#   2. Configures Gitea OAuth application for Woodpecker
#   3. Creates Woodpecker secrets from Vault
#   4. Activates pipelines for all Gitea repositories
#   5. Registers with the Orchestrator
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
WOODPECKER_URL="${WOODPECKER_URL:-http://omni-woodpecker-server:8000}"
GITEA_URL="${GITEA_URL:-http://omni-gitea:3000}"
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://omni-orchestrator:9500}"
MATTERMOST_WEBHOOK_URL="${MATTERMOST_WEBHOOK_URL:-http://omni-mattermost-webhook:8066/hooks/builds}"
NOTIFIER_URL="${NOTIFIER_URL:-http://omni-build-forge-notifier:8001}"

GITEA_ADMIN_USER="${GITEA_ADMIN_USER:-brendan}"
GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:-}"
WOODPECKER_ADMIN_TOKEN="${WOODPECKER_ADMIN_TOKEN:-}"

MAX_RETRIES=60
RETRY_INTERVAL=5

LOG_PREFIX="[build-forge-init]"

# =============================================================================
# Logging Helpers
# =============================================================================
log_info() {
    echo "{\"level\":\"info\",\"service\":\"build-forge-init\",\"msg\":\"$1\",\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
}

log_warn() {
    echo "{\"level\":\"warn\",\"service\":\"build-forge-init\",\"msg\":\"$1\",\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >&2
}

log_error() {
    echo "{\"level\":\"error\",\"service\":\"build-forge-init\",\"msg\":\"$1\",\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >&2
}

log_success() {
    echo "{\"level\":\"info\",\"service\":\"build-forge-init\",\"msg\":\"$1\",\"status\":\"success\",\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
}

# =============================================================================
# Health Check Utilities
# =============================================================================
wait_for_service() {
    local service_name="$1"
    local url="$2"
    local retries="${3:-$MAX_RETRIES}"
    local interval="${4:-$RETRY_INTERVAL}"

    log_info "Waiting for ${service_name} at ${url}..."

    for i in $(seq 1 "$retries"); do
        if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
            log_success "${service_name} is healthy (attempt ${i}/${retries})"
            return 0
        fi
        if [ "$i" -eq "$retries" ]; then
            log_error "${service_name} failed to become healthy after ${retries} attempts"
            return 1
        fi
        sleep "$interval"
    done
}

wait_for_postgres() {
    log_info "Waiting for PostgreSQL at omni-postgres:5432..."

    for i in $(seq 1 "$MAX_RETRIES"); do
        if pg_isready -h omni-postgres -p 5432 -U woodpecker -d woodpecker > /dev/null 2>&1; then
            log_success "PostgreSQL is healthy (attempt ${i}/${MAX_RETRIES})"
            return 0
        fi
        # Fallback: try TCP connect if pg_isready is not available
        if command -v nc &>/dev/null; then
            if nc -z omni-postgres 5432 2>/dev/null; then
                log_success "PostgreSQL TCP port is open (attempt ${i}/${MAX_RETRIES})"
                return 0
            fi
        fi
        if [ "$i" -eq "$MAX_RETRIES" ]; then
            log_error "PostgreSQL failed to become healthy after ${MAX_RETRIES} attempts"
            return 1
        fi
        sleep "$RETRY_INTERVAL"
    done
}

# =============================================================================
# Step 1: Wait for All Dependencies
# =============================================================================
wait_for_dependencies() {
    log_info "=== Step 1: Waiting for dependent services ==="

    wait_for_postgres

    wait_for_service "Gitea" "${GITEA_URL}/api/v1/version"

    wait_for_service "Vault" "${VAULT_ADDR}/v1/sys/health"

    wait_for_service "Woodpecker Server" "${WOODPECKER_URL}/healthz"

    wait_for_service "Notifier" "${NOTIFIER_URL}/health" 30 3

    log_success "All dependencies are healthy"
}

# =============================================================================
# Step 2: Configure Gitea OAuth Application
# =============================================================================
configure_gitea_oauth() {
    log_info "=== Step 2: Configuring Gitea OAuth application for Woodpecker ==="

    # Check if OAuth app already exists
    local existing_apps
    existing_apps=$(curl -sf \
        -u "${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}" \
        "${GITEA_URL}/api/v1/user/applications/oauth2" 2>/dev/null || echo "[]")

    local app_exists
    app_exists=$(echo "$existing_apps" | python3 -c "
import sys, json
apps = json.load(sys.stdin)
found = [a for a in apps if a.get('name') == 'woodpecker-ci']
print('true' if found else 'false')
" 2>/dev/null || echo "false")

    if [ "$app_exists" = "true" ]; then
        log_info "Gitea OAuth application 'woodpecker-ci' already exists"

        # Extract existing client ID
        local client_id
        client_id=$(echo "$existing_apps" | python3 -c "
import sys, json
apps = json.load(sys.stdin)
found = [a for a in apps if a.get('name') == 'woodpecker-ci']
if found:
    print(found[0].get('client_id', ''))
" 2>/dev/null || echo "")

        if [ -n "$client_id" ]; then
            log_info "Existing OAuth client_id: ${client_id}"
            GITEA_OAUTH_CLIENT_ID="$client_id"
        fi
        return 0
    fi

    # Create new OAuth application
    log_info "Creating Gitea OAuth application 'woodpecker-ci'..."

    local oauth_response
    oauth_response=$(curl -sf \
        -X POST \
        -u "${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"woodpecker-ci\",
            \"redirect_uris\": [\"${WOODPECKER_URL}/authorize\"],
            \"confidential_client\": true
        }" \
        "${GITEA_URL}/api/v1/user/applications/oauth2" 2>/dev/null)

    if [ -z "$oauth_response" ]; then
        log_error "Failed to create Gitea OAuth application"
        return 1
    fi

    GITEA_OAUTH_CLIENT_ID=$(echo "$oauth_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('client_id',''))" 2>/dev/null || echo "")
    GITEA_OAUTH_CLIENT_SECRET=$(echo "$oauth_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('client_secret',''))" 2>/dev/null || echo "")

    if [ -z "$GITEA_OAUTH_CLIENT_ID" ] || [ -z "$GITEA_OAUTH_CLIENT_SECRET" ]; then
        log_error "Failed to parse OAuth credentials from Gitea response"
        return 1
    fi

    log_success "Gitea OAuth application created (client_id: ${GITEA_OAUTH_CLIENT_ID})"

    # Store OAuth credentials in Vault
    log_info "Storing Gitea OAuth credentials in Vault..."

    curl -sf \
        -X POST \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"data\": {
                \"client_id\": \"${GITEA_OAUTH_CLIENT_ID}\",
                \"client_secret\": \"${GITEA_OAUTH_CLIENT_SECRET}\"
            }
        }" \
        "${VAULT_ADDR}/v1/secret/data/build-forge/gitea-oauth" > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        log_success "Gitea OAuth credentials stored in Vault at secret/build-forge/gitea-oauth"
    else
        log_warn "Failed to store Gitea OAuth credentials in Vault"
    fi
}

# =============================================================================
# Step 3: Create Woodpecker Secrets from Vault
# =============================================================================
create_woodpecker_secrets() {
    log_info "=== Step 3: Creating Woodpecker secrets from Vault ==="

    if [ -z "$WOODPECKER_ADMIN_TOKEN" ]; then
        log_warn "WOODPECKER_ADMIN_TOKEN not set — attempting to retrieve from Vault"
        WOODPECKER_ADMIN_TOKEN=$(curl -sf \
            -H "X-Vault-Token: ${VAULT_TOKEN}" \
            "${VAULT_ADDR}/v1/secret/data/build-forge/woodpecker-admin" \
            | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['data']['api_token'])" 2>/dev/null || echo "")

        if [ -z "$WOODPECKER_ADMIN_TOKEN" ]; then
            log_error "Cannot retrieve Woodpecker admin API token from Vault"
            return 1
        fi
    fi

    local wp_auth_header="Authorization: Bearer ${WOODPECKER_ADMIN_TOKEN}"

    # Define secrets to create: name -> vault_path -> vault_key
    declare -A SECRETS_MAP
    SECRETS_MAP=(
        ["cosign_private_key"]="secret/data/build-forge/cosign:private_key"
        ["cosign_password"]="secret/data/build-forge/cosign:password"
        ["vault_token"]="secret/data/build-forge/vault:token"
        ["coolify_api_token"]="secret/data/build-forge/coolify:api_token"
        ["mattermost_webhook_url"]="secret/data/build-forge/mattermost:webhook_url"
        ["registry_username"]="secret/data/build-forge/registry:username"
        ["registry_password"]="secret/data/build-forge/registry:password"
        ["gitea_client_id"]="secret/data/build-forge/gitea-oauth:client_id"
        ["gitea_client_secret"]="secret/data/build-forge/gitea-oauth:client_secret"
    )

    local secrets_created=0
    local secrets_failed=0

    for secret_name in "${!SECRETS_MAP[@]}"; do
        local vault_ref="${SECRETS_MAP[$secret_name]}"
        local vault_path="${vault_ref%%:*}"
        local vault_key="${vault_ref##*:}"

        log_info "Fetching secret '${secret_name}' from Vault (${vault_path}:${vault_key})..."

        local secret_value
        secret_value=$(curl -sf \
            -H "X-Vault-Token: ${VAULT_TOKEN}" \
            "${VAULT_ADDR}/v1/${vault_path}" \
            | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['data']['${vault_key}'])" 2>/dev/null || echo "")

        if [ -z "$secret_value" ]; then
            log_warn "Secret '${secret_name}' not found in Vault at ${vault_path}:${vault_key} — using placeholder"
            secret_value="VAULT_PLACEHOLDER_${secret_name}"
        fi

        # Check if secret already exists in Woodpecker (global org secrets)
        local existing
        existing=$(curl -sf \
            -H "$wp_auth_header" \
            "${WOODPECKER_URL}/api/secrets" 2>/dev/null | \
            python3 -c "
import sys, json
secrets = json.load(sys.stdin)
found = [s for s in secrets if s.get('name') == '${secret_name}']
print('true' if found else 'false')
" 2>/dev/null || echo "false")

        if [ "$existing" = "true" ]; then
            # Update existing secret
            local update_response
            update_response=$(curl -sf \
                -X PATCH \
                -H "$wp_auth_header" \
                -H "Content-Type: application/json" \
                -d "{
                    \"name\": \"${secret_name}\",
                    \"value\": \"${secret_value}\",
                    \"events\": [\"push\", \"pull_request\", \"tag\", \"deployment\"],
                    \"images\": []
                }" \
                "${WOODPECKER_URL}/api/secrets/${secret_name}" 2>/dev/null)

            if [ $? -eq 0 ]; then
                log_info "Updated existing Woodpecker secret: ${secret_name}"
                secrets_created=$((secrets_created + 1))
            else
                log_warn "Failed to update Woodpecker secret: ${secret_name}"
                secrets_failed=$((secrets_failed + 1))
            fi
        else
            # Create new secret
            local create_response
            create_response=$(curl -sf \
                -X POST \
                -H "$wp_auth_header" \
                -H "Content-Type: application/json" \
                -d "{
                    \"name\": \"${secret_name}\",
                    \"value\": \"${secret_value}\",
                    \"events\": [\"push\", \"pull_request\", \"tag\", \"deployment\"],
                    \"images\": []
                }" \
                "${WOODPECKER_URL}/api/secrets" 2>/dev/null)

            if [ $? -eq 0 ]; then
                log_success "Created Woodpecker secret: ${secret_name}"
                secrets_created=$((secrets_created + 1))
            else
                log_warn "Failed to create Woodpecker secret: ${secret_name}"
                secrets_failed=$((secrets_failed + 1))
            fi
        fi
    done

    log_info "Secrets summary: ${secrets_created} created/updated, ${secrets_failed} failed"

    if [ "$secrets_failed" -gt 0 ]; then
        log_warn "Some secrets could not be created — pipelines may fail until resolved"
    fi
}

# =============================================================================
# Step 4: Activate Pipelines for Gitea Repositories
# =============================================================================
activate_gitea_repos() {
    log_info "=== Step 4: Activating pipelines for Gitea repositories ==="

    local wp_auth_header="Authorization: Bearer ${WOODPECKER_ADMIN_TOKEN}"

    # Fetch all repos from Woodpecker (which syncs from Gitea)
    log_info "Syncing repositories from Gitea..."

    # Trigger repo sync
    curl -sf \
        -X POST \
        -H "$wp_auth_header" \
        "${WOODPECKER_URL}/api/repos/repair" > /dev/null 2>&1 || true

    # Wait a moment for sync
    sleep 5

    # Get list of repos
    local repos_json
    repos_json=$(curl -sf \
        -H "$wp_auth_header" \
        "${WOODPECKER_URL}/api/repos?all=true" 2>/dev/null || echo "[]")

    local repo_count
    repo_count=$(echo "$repos_json" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

    log_info "Found ${repo_count} repositories from Gitea"

    if [ "$repo_count" -eq 0 ]; then
        log_warn "No repositories found — they may not be synced yet"
        return 0
    fi

    # Activate each repo
    local activated=0
    local already_active=0
    local failed=0

    local repo_ids
    repo_ids=$(echo "$repos_json" | python3 -c "
import sys, json
repos = json.load(sys.stdin)
for r in repos:
    active = 'active' if r.get('active', False) else 'inactive'
    print(f\"{r.get('id', 0)}|{r.get('full_name', 'unknown')}|{active}\")
" 2>/dev/null || echo "")

    while IFS='|' read -r repo_id repo_full_name repo_status; do
        [ -z "$repo_id" ] && continue

        if [ "$repo_status" = "active" ]; then
            log_info "Repository '${repo_full_name}' is already active"
            already_active=$((already_active + 1))
            continue
        fi

        log_info "Activating repository: ${repo_full_name} (id: ${repo_id})..."

        local activate_response
        activate_response=$(curl -sf \
            -X POST \
            -H "$wp_auth_header" \
            "${WOODPECKER_URL}/api/repos/${repo_id}" 2>/dev/null)

        if [ $? -eq 0 ]; then
            log_success "Activated repository: ${repo_full_name}"
            activated=$((activated + 1))
        else
            log_warn "Failed to activate repository: ${repo_full_name}"
            failed=$((failed + 1))
        fi
    done <<< "$repo_ids"

    log_info "Repository activation summary: ${activated} activated, ${already_active} already active, ${failed} failed"
}

# =============================================================================
# Step 5: Register with Orchestrator
# =============================================================================
register_with_orchestrator() {
    log_info "=== Step 5: Registering Build Forge with Orchestrator ==="

    local registration_payload
    registration_payload=$(cat << 'JSONEOF'
{
    "service": "build-forge",
    "system_id": 35,
    "version": "1.0.0",
    "components": [
        {
            "name": "woodpecker-server",
            "type": "ci-server",
            "url": "http://omni-woodpecker-server:8000",
            "health_endpoint": "/healthz",
            "metrics_endpoint": ":9100/metrics",
            "port": 8000
        },
        {
            "name": "woodpecker-agent-1",
            "type": "ci-agent",
            "mode": "docker-socket",
            "max_procs": 2
        },
        {
            "name": "woodpecker-agent-2",
            "type": "ci-agent",
            "mode": "docker-in-docker",
            "max_procs": 2
        },
        {
            "name": "notifier",
            "type": "notification-relay",
            "url": "http://omni-build-forge-notifier:8001",
            "health_endpoint": "/health",
            "metrics_endpoint": "/metrics",
            "port": 8001
        }
    ],
    "integrations": [
        {"service": "gitea", "url": "http://omni-gitea:3000", "type": "forge"},
        {"service": "code-scorer", "url": "http://omni-code-scorer", "type": "ai-review"},
        {"service": "gate-engine", "url": "http://omni-gate-engine", "type": "quality-gate"},
        {"service": "vault", "url": "http://omni-vault:8200", "type": "secrets"},
        {"service": "coolify", "url": "http://omni-coolify:8000", "type": "deployment"},
        {"service": "mattermost", "url": "http://omni-mattermost-webhook:8066", "type": "notification"},
        {"service": "omi-bridge", "url": "http://omni-omi-bridge:9700", "type": "haptic"},
        {"service": "langfuse", "url": "http://omni-langfuse:3000", "type": "observability"},
        {"service": "minio", "url": "http://omni-minio:9000", "type": "artifacts"},
        {"service": "postgres", "url": "omni-postgres:5432", "type": "database"}
    ],
    "pipeline_templates": [
        "python-fastapi",
        "typescript-nextjs",
        "go",
        "rust"
    ],
    "capabilities": [
        "ci-cd",
        "container-build",
        "container-scan",
        "sbom-generation",
        "image-signing",
        "ai-code-review",
        "quality-gates",
        "staging-deployment",
        "production-deployment",
        "load-testing",
        "notifications",
        "haptic-feedback"
    ]
}
JSONEOF
)

    local register_response
    register_response=$(curl -sf \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$registration_payload" \
        "${ORCHESTRATOR_URL}/api/services/register" 2>/dev/null)

    if [ $? -eq 0 ]; then
        log_success "Registered Build Forge with Orchestrator"
        log_info "Orchestrator response: ${register_response}"
    else
        log_warn "Failed to register with Orchestrator — it may not be running yet"
        log_info "Build Forge will function independently"
    fi
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    log_info "============================================================"
    log_info "System 35 — Build Forge Initialization"
    log_info "Omni Quantum Elite AI Coding System"
    log_info "============================================================"

    local start_time
    start_time=$(date +%s)

    # Step 1: Wait for dependencies
    wait_for_dependencies || {
        log_error "Dependency health checks failed — aborting initialization"
        exit 1
    }

    # Step 2: Configure Gitea OAuth
    configure_gitea_oauth || {
        log_error "Gitea OAuth configuration failed — aborting"
        exit 1
    }

    # Step 3: Create Woodpecker secrets from Vault
    create_woodpecker_secrets || {
        log_warn "Secret creation had issues — continuing with warnings"
    }

    # Step 4: Activate pipelines for Gitea repos
    activate_gitea_repos || {
        log_warn "Repository activation had issues — continuing with warnings"
    }

    # Step 5: Register with Orchestrator
    register_with_orchestrator || {
        log_warn "Orchestrator registration failed — non-critical, continuing"
    }

    local end_time
    end_time=$(date +%s)
    local elapsed=$((end_time - start_time))

    log_info "============================================================"
    log_success "Build Forge initialization completed in ${elapsed}s"
    log_info "  Woodpecker Server: ${WOODPECKER_URL}"
    log_info "  Notifier:          ${NOTIFIER_URL}"
    log_info "  Gitea:             ${GITEA_URL}"
    log_info "  Vault:             ${VAULT_ADDR}"
    log_info "============================================================"
}

main "$@"
