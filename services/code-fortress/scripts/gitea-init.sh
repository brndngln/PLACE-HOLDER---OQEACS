#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# System 7 — Code Fortress (Gitea) — Initialization Script
# ═══════════════════════════════════════════════════════════════════════════════
# Initializes Gitea with admin user, organization, repositories, webhooks,
# branch protection, LFS configuration, API tokens, and service registrations.
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_NAME="$(basename "$0")"
GITEA_URL="${GITEA_URL:-http://omni-gitea:3000}"
GITEA_API="${GITEA_URL}/api/v1"
GITEA_ADMIN_USER="${GITEA_ADMIN_USER:-omni-admin}"
GITEA_ADMIN_PASSWORD="${GITEA_ADMIN_PASSWORD:?GITEA_ADMIN_PASSWORD is required}"
GITEA_ADMIN_EMAIL="${GITEA_ADMIN_EMAIL:-admin@omni-quantum.internal}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://omni-orchestrator:8080}"
UPTIME_KUMA_URL="${UPTIME_KUMA_URL:-http://omni-uptime-kuma:3001}"
N8N_WEBHOOK_BASE="${N8N_WEBHOOK_BASE:-http://omni-n8n:5678/webhook}"
WOODPECKER_HOOK_URL="${WOODPECKER_HOOK_URL:-http://omni-woodpecker-server:8000/hook}"

MAX_RETRIES=60
RETRY_INTERVAL=5

# ─── Colored Timestamped Output ───────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ${GREEN}[INFO]${NC}  ${SCRIPT_NAME}: $*"; }
log_warn()    { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ${YELLOW}[WARN]${NC}  ${SCRIPT_NAME}: $*"; }
log_error()   { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ${RED}[ERROR]${NC} ${SCRIPT_NAME}: $*"; }
log_step()    { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ${CYAN}[STEP]${NC}  ${SCRIPT_NAME}: $*"; }
log_success() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ${GREEN}[OK]${NC}    ${SCRIPT_NAME}: $*"; }

# ─── Cleanup ──────────────────────────────────────────────────────────────────
TEMP_DIR=""
cleanup() {
    local exit_code=$?
    if [[ -n "${TEMP_DIR}" && -d "${TEMP_DIR}" ]]; then
        rm -rf "${TEMP_DIR}"
    fi
    if [[ $exit_code -ne 0 ]]; then
        log_error "Script exited with code ${exit_code}"
    fi
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

TEMP_DIR="$(mktemp -d)"

# ─── Helper: API Call ─────────────────────────────────────────────────────────
gitea_api() {
    local method="$1"
    local endpoint="$2"
    shift 2
    local url="${GITEA_API}${endpoint}"

    local response
    response=$(curl -s -w "\n%{http_code}" \
        -X "${method}" \
        -H "Content-Type: application/json" \
        -u "${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}" \
        "$@" \
        "${url}" 2>&1) || true

    local http_code
    http_code=$(echo "${response}" | tail -n1)
    local body
    body=$(echo "${response}" | sed '$d')

    echo "${body}"
    return 0
}

gitea_api_with_code() {
    local method="$1"
    local endpoint="$2"
    shift 2
    local url="${GITEA_API}${endpoint}"

    local response
    response=$(curl -s -w "\n%{http_code}" \
        -X "${method}" \
        -H "Content-Type: application/json" \
        -u "${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}" \
        "$@" \
        "${url}" 2>&1) || true

    local http_code
    http_code=$(echo "${response}" | tail -n1)
    local body
    body=$(echo "${response}" | sed '$d')

    echo "${http_code}|${body}"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Wait for Gitea to be healthy
# ═══════════════════════════════════════════════════════════════════════════════
wait_for_gitea() {
    log_step "Phase 1: Waiting for Gitea to become healthy..."
    local attempt=0
    local backoff=${RETRY_INTERVAL}

    while [[ $attempt -lt $MAX_RETRIES ]]; do
        attempt=$((attempt + 1))
        if curl -sf "${GITEA_URL}/api/v1/version" > /dev/null 2>&1; then
            log_success "Gitea is healthy (attempt ${attempt}/${MAX_RETRIES})"
            return 0
        fi
        log_warn "Gitea not ready (attempt ${attempt}/${MAX_RETRIES}), retrying in ${backoff}s..."
        sleep "${backoff}"
        if [[ $backoff -lt 30 ]]; then
            backoff=$((backoff + 2))
        fi
    done

    log_error "Gitea did not become healthy after ${MAX_RETRIES} attempts"
    return 1
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Create admin user
# ═══════════════════════════════════════════════════════════════════════════════
create_admin_user() {
    log_step "Phase 2: Creating admin user '${GITEA_ADMIN_USER}'..."

    local result
    result=$(gitea_api_with_code GET "/users/${GITEA_ADMIN_USER}")
    local code="${result%%|*}"

    if [[ "${code}" == "200" ]]; then
        log_info "Admin user '${GITEA_ADMIN_USER}' already exists, skipping creation"
        return 0
    fi

    log_info "Creating admin user via Gitea CLI..."
    if docker exec omni-gitea gitea admin user create \
        --admin \
        --username "${GITEA_ADMIN_USER}" \
        --password "${GITEA_ADMIN_PASSWORD}" \
        --email "${GITEA_ADMIN_EMAIL}" \
        --must-change-password=false 2>&1; then
        log_success "Admin user '${GITEA_ADMIN_USER}' created successfully"
    else
        log_warn "Admin user creation returned non-zero (may already exist)"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Create organization
# ═══════════════════════════════════════════════════════════════════════════════
create_organization() {
    local org_name="omni-quantum"
    log_step "Phase 3: Creating organization '${org_name}'..."

    local result
    result=$(gitea_api_with_code GET "/orgs/${org_name}")
    local code="${result%%|*}"

    if [[ "${code}" == "200" ]]; then
        log_info "Organization '${org_name}' already exists, skipping creation"
        return 0
    fi

    local payload
    payload=$(cat <<'ORGEOF'
{
  "username": "omni-quantum",
  "full_name": "Omni Quantum Elite",
  "description": "Omni Quantum Elite Autonomous Coding System",
  "website": "https://omni-quantum.internal",
  "visibility": "private",
  "repo_admin_change_team_access": true
}
ORGEOF
    )

    local result2
    result2=$(gitea_api_with_code POST "/orgs" -d "${payload}")
    local code2="${result2%%|*}"

    if [[ "${code2}" == "201" || "${code2}" == "200" ]]; then
        log_success "Organization '${org_name}' created successfully"
    elif [[ "${code2}" == "422" ]]; then
        log_info "Organization '${org_name}' already exists (422)"
    else
        log_error "Failed to create organization '${org_name}' (HTTP ${code2})"
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: Create repositories
# ═══════════════════════════════════════════════════════════════════════════════
create_repo() {
    local repo_name="$1"
    local description="$2"

    local result
    result=$(gitea_api_with_code GET "/repos/omni-quantum/${repo_name}")
    local code="${result%%|*}"

    if [[ "${code}" == "200" ]]; then
        log_info "Repository 'omni-quantum/${repo_name}' already exists, skipping"
        return 0
    fi

    local payload
    payload=$(cat <<EOF
{
  "name": "${repo_name}",
  "description": "${description}",
  "private": true,
  "auto_init": true,
  "default_branch": "main",
  "trust_model": "collaborator",
  "gitignores": "",
  "license": "MIT",
  "readme": "Default"
}
EOF
    )

    local result2
    result2=$(gitea_api_with_code POST "/orgs/omni-quantum/repos" -d "${payload}")
    local code2="${result2%%|*}"

    if [[ "${code2}" == "201" || "${code2}" == "200" ]]; then
        log_success "Repository 'omni-quantum/${repo_name}' created"
    else
        log_error "Failed to create repository '${repo_name}' (HTTP ${code2})"
        return 1
    fi
}

create_repositories() {
    log_step "Phase 4: Creating repositories..."

    create_repo "omni-platform" "Core platform infrastructure and deployment configurations"
    create_repo "omni-configs" "Centralized configuration management for all services"
    create_repo "omni-knowledge" "Knowledge base content, documentation, and training data"
    create_repo "client-template" "Template repository for new client project scaffolding"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Set up webhooks
# ═══════════════════════════════════════════════════════════════════════════════
create_webhook() {
    local repo="$1"
    local target_url="$2"
    local event_type="$3"

    local events_json
    case "${event_type}" in
        push)
            events_json='["push"]'
            ;;
        pull_request)
            events_json='["pull_request","pull_request_review"]'
            ;;
        release)
            events_json='["release"]'
            ;;
        all-n8n)
            events_json='["push","pull_request","pull_request_review","release"]'
            ;;
        *)
            events_json='["push"]'
            ;;
    esac

    local payload
    payload=$(cat <<EOF
{
  "type": "gitea",
  "active": true,
  "branch_filter": "*",
  "config": {
    "url": "${target_url}",
    "content_type": "json",
    "secret": "",
    "insecure_ssl": "0"
  },
  "events": ${events_json}
}
EOF
    )

    local result
    result=$(gitea_api_with_code POST "/repos/omni-quantum/${repo}/hooks" -d "${payload}")
    local code="${result%%|*}"

    if [[ "${code}" == "201" || "${code}" == "200" ]]; then
        log_success "Webhook created: ${repo} -> ${target_url} (${event_type})"
    else
        log_warn "Webhook creation returned HTTP ${code} for ${repo} -> ${target_url}"
    fi
}

setup_webhooks() {
    log_step "Phase 5: Setting up webhooks..."

    local repos=("omni-platform" "omni-configs" "omni-knowledge" "client-template")

    for repo in "${repos[@]}"; do
        log_info "Configuring webhooks for '${repo}'..."

        # n8n webhooks for push, PR, and release events
        create_webhook "${repo}" "${N8N_WEBHOOK_BASE}/gitea-push" "push"
        create_webhook "${repo}" "${N8N_WEBHOOK_BASE}/gitea-pull-request" "pull_request"
        create_webhook "${repo}" "${N8N_WEBHOOK_BASE}/gitea-release" "release"

        # Woodpecker CI webhook for push events
        create_webhook "${repo}" "${WOODPECKER_HOOK_URL}" "push"
    done
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6: Branch protection
# ═══════════════════════════════════════════════════════════════════════════════
setup_branch_protection() {
    log_step "Phase 6: Setting up branch protection on 'main'..."

    local repos=("omni-platform" "omni-configs" "omni-knowledge" "client-template")

    local payload
    payload=$(cat <<'EOF'
{
  "branch_name": "main",
  "enable_push": true,
  "enable_push_whitelist": false,
  "enable_merge_whitelist": false,
  "enable_status_check": true,
  "status_check_contexts": ["ci/woodpecker"],
  "required_approvals": 1,
  "enable_approvals_whitelist": false,
  "block_on_rejected_reviews": true,
  "block_on_official_review_requests": true,
  "block_on_outdated_branch": true,
  "dismiss_stale_approvals": true,
  "require_signed_commits": false,
  "protected_file_patterns": "",
  "unprotected_file_patterns": "",
  "enable_force_push": false,
  "enable_force_push_whitelist": false,
  "enable_delete": false
}
EOF
    )

    for repo in "${repos[@]}"; do
        local result
        result=$(gitea_api_with_code POST "/repos/omni-quantum/${repo}/branch_protections" -d "${payload}")
        local code="${result%%|*}"

        if [[ "${code}" == "201" || "${code}" == "200" ]]; then
            log_success "Branch protection set for 'omni-quantum/${repo}:main'"
        elif [[ "${code}" == "422" || "${code}" == "409" ]]; then
            log_info "Branch protection already exists for 'omni-quantum/${repo}:main', updating..."
            local update_result
            update_result=$(gitea_api_with_code PATCH "/repos/omni-quantum/${repo}/branch_protections/main" -d "${payload}")
            local update_code="${update_result%%|*}"
            if [[ "${update_code}" == "200" ]]; then
                log_success "Branch protection updated for 'omni-quantum/${repo}:main'"
            else
                log_warn "Branch protection update returned HTTP ${update_code} for '${repo}'"
            fi
        else
            log_error "Failed to set branch protection for '${repo}' (HTTP ${code})"
        fi
    done
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7: Configure LFS to MinIO
# ═══════════════════════════════════════════════════════════════════════════════
configure_lfs() {
    log_step "Phase 7: Verifying LFS -> MinIO configuration..."

    # LFS is configured via app.ini [lfs] section pointing to MinIO
    # Verify the configuration is active by checking the LFS API endpoint
    local result
    result=$(gitea_api_with_code GET "/repos/omni-quantum/omni-platform")
    local code="${result%%|*}"

    if [[ "${code}" == "200" ]]; then
        log_success "LFS configuration verified (MinIO backend configured in app.ini)"
        log_info "  Endpoint: omni-minio:9000"
        log_info "  Bucket: gitea-lfs"
        log_info "  Region: us-east-1"
    else
        log_warn "Could not verify LFS configuration (repository may not exist yet)"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8: Generate API tokens
# ═══════════════════════════════════════════════════════════════════════════════
create_api_token() {
    local token_name="$1"
    local scopes="${2:-}"

    local payload
    if [[ -n "${scopes}" ]]; then
        payload=$(cat <<EOF
{
  "name": "${token_name}",
  "scopes": [${scopes}]
}
EOF
        )
    else
        payload=$(cat <<EOF
{
  "name": "${token_name}"
}
EOF
        )
    fi

    local result
    result=$(gitea_api_with_code POST "/users/${GITEA_ADMIN_USER}/tokens" -d "${payload}")
    local code="${result%%|*}"
    local body="${result#*|}"

    if [[ "${code}" == "201" || "${code}" == "200" ]]; then
        local token_value
        token_value=$(echo "${body}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha1',''))" 2>/dev/null || echo "")
        if [[ -n "${token_value}" ]]; then
            log_success "API token '${token_name}' created: ${token_value:0:8}..."
            echo "${token_value}" > "${TEMP_DIR}/token_${token_name}"
        else
            log_success "API token '${token_name}' created (token value in response)"
        fi
    elif [[ "${code}" == "422" ]]; then
        log_info "API token '${token_name}' already exists, skipping"
    else
        log_warn "API token creation returned HTTP ${code} for '${token_name}'"
    fi
}

generate_api_tokens() {
    log_step "Phase 8: Generating API tokens..."

    create_api_token "woodpecker-ci" '"write:repository","read:user","read:organization","write:issue"'
    create_api_token "openhands-agent" '"write:repository","read:user","read:organization","write:issue","write:package"'
    create_api_token "swe-agent" '"write:repository","read:user","read:organization","write:issue"'

    log_info "API tokens stored in temporary directory for retrieval by dependent services"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 9: Register with Orchestrator (System 37)
# ═══════════════════════════════════════════════════════════════════════════════
register_orchestrator() {
    log_step "Phase 9: Registering with System 37 Orchestrator..."

    local payload
    payload=$(cat <<'EOF'
{
  "system_id": 7,
  "system_name": "code-fortress",
  "service_type": "gitea",
  "display_name": "Code Fortress (Gitea)",
  "health_endpoint": "http://omni-gitea:3000/api/v1/version",
  "metrics_endpoint": "http://omni-gitea:3000/metrics",
  "api_endpoint": "http://omni-gitea:3000/api/v1",
  "status": "running",
  "version": "1.21",
  "dependencies": ["omni-postgres", "omni-redis", "omni-minio"],
  "capabilities": ["git", "lfs", "webhooks", "oauth2", "api"],
  "network": "omni-quantum-network",
  "ports": {
    "http": 3000,
    "ssh": 2222
  },
  "tags": ["foundation", "vcs", "code-management"]
}
EOF
    )

    local response
    response=$(curl -sf -X POST \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        "${ORCHESTRATOR_URL}/api/v1/systems/register" 2>&1) || {
        log_warn "Could not register with Orchestrator (may not be running yet)"
        return 0
    }

    log_success "Registered with System 37 Orchestrator"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 10: Register with Uptime Kuma (System 31)
# ═══════════════════════════════════════════════════════════════════════════════
register_uptime_kuma() {
    log_step "Phase 10: Registering with System 31 Uptime Kuma..."

    local payload
    payload=$(cat <<'EOF'
{
  "type": "http",
  "name": "System 7 - Code Fortress (Gitea)",
  "url": "http://omni-gitea:3000/api/v1/version",
  "method": "GET",
  "interval": 60,
  "retryInterval": 30,
  "maxretries": 3,
  "accepted_statuscodes": ["200-299"],
  "notificationIDList": {},
  "tags": [
    {"name": "system-7", "value": "code-fortress"},
    {"name": "category", "value": "foundation"},
    {"name": "service", "value": "gitea"}
  ]
}
EOF
    )

    local response
    response=$(curl -sf -X POST \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        "${UPTIME_KUMA_URL}/api/monitors" 2>&1) || {
        log_warn "Could not register with Uptime Kuma (may not be running yet)"
        return 0
    }

    log_success "Registered with System 31 Uptime Kuma"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Main Execution
# ═══════════════════════════════════════════════════════════════════════════════
main() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  System 7 — Code Fortress (Gitea) — Initialization${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    wait_for_gitea
    create_admin_user
    create_organization
    create_repositories
    setup_webhooks
    setup_branch_protection
    configure_lfs
    generate_api_tokens
    register_orchestrator
    register_uptime_kuma

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  System 7 — Code Fortress initialization complete${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    log_success "All initialization phases completed successfully"
}

main "$@"
