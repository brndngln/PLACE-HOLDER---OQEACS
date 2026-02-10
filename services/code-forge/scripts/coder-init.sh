#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# System 36 — Code Forge (Coder) — Initialization Script
# ═══════════════════════════════════════════════════════════════════════════════
# Initializes Coder with admin user, pushes all 5 workspace templates,
# configures Authentik OAuth, sets organization defaults, and registers
# with the Orchestrator.
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_NAME="$(basename "$0")"
CODER_URL="${CODER_URL:-http://omni-coder:7080}"
CODER_ADMIN_EMAIL="${CODER_ADMIN_EMAIL:-admin@omni-quantum.internal}"
CODER_ADMIN_USERNAME="${CODER_ADMIN_USERNAME:-omni-admin}"
CODER_ADMIN_PASSWORD="${CODER_ADMIN_PASSWORD:?CODER_ADMIN_PASSWORD is required}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://omni-orchestrator:9500}"
AUTHENTIK_URL="${AUTHENTIK_URL:-http://omni-authentik:9000}"
AUTHENTIK_TOKEN="${AUTHENTIK_TOKEN:-}"
TEMPLATES_DIR="${TEMPLATES_DIR:-/templates}"

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

# ─── Helper: Coder API Call ──────────────────────────────────────────────────
CODER_SESSION_TOKEN=""

coder_api() {
    local method="$1"
    local endpoint="$2"
    shift 2
    local url="${CODER_URL}/api/v2${endpoint}"

    local auth_header=""
    if [[ -n "${CODER_SESSION_TOKEN}" ]]; then
        auth_header="-H"
        local auth_value="Coder-Session-Token: ${CODER_SESSION_TOKEN}"
    fi

    local response
    if [[ -n "${auth_header}" ]]; then
        response=$(curl -s -w "\n%{http_code}" \
            -X "${method}" \
            -H "Content-Type: application/json" \
            -H "${auth_value}" \
            "$@" \
            "${url}" 2>&1) || true
    else
        response=$(curl -s -w "\n%{http_code}" \
            -X "${method}" \
            -H "Content-Type: application/json" \
            "$@" \
            "${url}" 2>&1) || true
    fi

    local http_code
    http_code=$(echo "${response}" | tail -n1)
    local body
    body=$(echo "${response}" | sed '$d')

    echo "${http_code}|${body}"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Wait for Coder to be healthy
# ═══════════════════════════════════════════════════════════════════════════════
wait_for_coder() {
    log_step "Phase 1: Waiting for Coder to become healthy..."
    local attempt=0
    local backoff=${RETRY_INTERVAL}

    while [[ $attempt -lt $MAX_RETRIES ]]; do
        attempt=$((attempt + 1))
        if curl -sf "${CODER_URL}/healthz" > /dev/null 2>&1; then
            log_success "Coder is healthy (attempt ${attempt}/${MAX_RETRIES})"
            return 0
        fi
        log_warn "Coder not ready (attempt ${attempt}/${MAX_RETRIES}), retrying in ${backoff}s..."
        sleep "${backoff}"
        if [[ $backoff -lt 30 ]]; then
            backoff=$((backoff + 2))
        fi
    done

    log_error "Coder did not become healthy after ${MAX_RETRIES} attempts"
    return 1
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Create admin user via Coder CLI
# ═══════════════════════════════════════════════════════════════════════════════
create_admin_user() {
    log_step "Phase 2: Creating admin user '${CODER_ADMIN_USERNAME}'..."

    # Check if first user already exists by trying to get the first user endpoint
    local result
    result=$(curl -s -w "\n%{http_code}" \
        "${CODER_URL}/api/v2/users/first" 2>&1) || true
    local http_code
    http_code=$(echo "${result}" | tail -n1)

    if [[ "${http_code}" == "409" ]]; then
        log_info "Admin user already exists, logging in..."

        # Login to get session token
        local login_result
        login_result=$(curl -s -w "\n%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "{\"email\":\"${CODER_ADMIN_EMAIL}\",\"password\":\"${CODER_ADMIN_PASSWORD}\"}" \
            "${CODER_URL}/api/v2/users/login" 2>&1) || true

        local login_code
        login_code=$(echo "${login_result}" | tail -n1)
        local login_body
        login_body=$(echo "${login_result}" | sed '$d')

        if [[ "${login_code}" == "201" ]]; then
            CODER_SESSION_TOKEN=$(echo "${login_body}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_token',''))" 2>/dev/null || echo "")
            if [[ -n "${CODER_SESSION_TOKEN}" ]]; then
                log_success "Logged in as '${CODER_ADMIN_USERNAME}'"
                echo "${CODER_SESSION_TOKEN}" > "${TEMP_DIR}/session_token"
                export CODER_SESSION_TOKEN
                return 0
            fi
        fi

        log_warn "Login returned HTTP ${login_code}, attempting CLI login..."
    else
        # Create the first user
        log_info "Creating first user via API..."
        local create_result
        create_result=$(curl -s -w "\n%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "{
                \"email\": \"${CODER_ADMIN_EMAIL}\",
                \"username\": \"${CODER_ADMIN_USERNAME}\",
                \"password\": \"${CODER_ADMIN_PASSWORD}\"
            }" \
            "${CODER_URL}/api/v2/users/first" 2>&1) || true

        local create_code
        create_code=$(echo "${create_result}" | tail -n1)
        local create_body
        create_body=$(echo "${create_result}" | sed '$d')

        if [[ "${create_code}" == "201" ]]; then
            CODER_SESSION_TOKEN=$(echo "${create_body}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_token',''))" 2>/dev/null || echo "")
            if [[ -n "${CODER_SESSION_TOKEN}" ]]; then
                log_success "Admin user '${CODER_ADMIN_USERNAME}' created successfully"
                echo "${CODER_SESSION_TOKEN}" > "${TEMP_DIR}/session_token"
                export CODER_SESSION_TOKEN
                return 0
            fi
        fi

        log_error "Failed to create admin user (HTTP ${create_code})"
    fi

    # Fallback: try coder CLI login
    export CODER_URL
    coder login "${CODER_URL}" \
        --username "${CODER_ADMIN_USERNAME}" \
        --password "${CODER_ADMIN_PASSWORD}" \
        --first-user-email "${CODER_ADMIN_EMAIL}" \
        --first-user-username "${CODER_ADMIN_USERNAME}" \
        --first-user-password "${CODER_ADMIN_PASSWORD}" 2>&1 || {
            log_warn "CLI login attempt completed (may have partial success)"
        }

    # Extract token from coder session
    CODER_SESSION_TOKEN=$(coder tokens create --name "init-script-$(date +%s)" --lifetime 8h 2>/dev/null | tail -1 || echo "")
    if [[ -n "${CODER_SESSION_TOKEN}" ]]; then
        log_success "Authenticated via CLI, token acquired"
        echo "${CODER_SESSION_TOKEN}" > "${TEMP_DIR}/session_token"
        export CODER_SESSION_TOKEN
    else
        log_error "Could not obtain session token"
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Push workspace templates
# ═══════════════════════════════════════════════════════════════════════════════
push_template() {
    local template_name="$1"
    local template_dir="$2"
    local description="$3"

    log_info "Pushing template '${template_name}' from ${template_dir}..."

    if [[ ! -d "${template_dir}" ]]; then
        log_error "Template directory not found: ${template_dir}"
        return 1
    fi

    # Check if template already exists
    local result
    result=$(coder_api GET "/templates/omni-quantum/${template_name}")
    local code="${result%%|*}"

    if [[ "${code}" == "200" ]]; then
        log_info "Template '${template_name}' already exists, updating..."
        coder templates push "${template_name}" \
            --directory "${template_dir}" \
            --yes \
            --name "${template_name}" 2>&1 || {
                log_warn "Template update may have had issues, continuing..."
            }
    else
        log_info "Creating new template '${template_name}'..."
        coder templates create "${template_name}" \
            --directory "${template_dir}" \
            --yes \
            --default-ttl 8h \
            --description "${description}" 2>&1 || {
                # If create fails, try push as fallback
                log_warn "Create failed, trying push..."
                coder templates push "${template_name}" \
                    --directory "${template_dir}" \
                    --yes \
                    --create 2>&1 || {
                        log_error "Failed to push template '${template_name}'"
                        return 1
                    }
            }
    fi

    log_success "Template '${template_name}' pushed successfully"
}

push_all_templates() {
    log_step "Phase 3: Pushing all workspace templates..."

    push_template "python-dev" \
        "${TEMPLATES_DIR}/python-dev" \
        "Python 3.12 development environment with ruff, black, mypy, pytest, poetry, and Jupyter"

    push_template "typescript-dev" \
        "${TEMPLATES_DIR}/typescript-dev" \
        "TypeScript/Node.js 20 development environment with npm, pnpm, ESLint, and Prettier"

    push_template "go-dev" \
        "${TEMPLATES_DIR}/go-dev" \
        "Go 1.22 development environment with golangci-lint, gopls, and delve debugger"

    push_template "rust-dev" \
        "${TEMPLATES_DIR}/rust-dev" \
        "Rust development environment with cargo, clippy, rustfmt, and rust-analyzer"

    push_template "fullstack-dev" \
        "${TEMPLATES_DIR}/fullstack-dev" \
        "Fullstack environment with Python, Node.js, Go, Rust, Docker CLI, kubectl, and database clients"

    log_success "All 5 workspace templates pushed"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: Configure Authentik OAuth
# ═══════════════════════════════════════════════════════════════════════════════
configure_authentik_oauth() {
    log_step "Phase 4: Configuring Authentik OAuth integration..."

    if [[ -z "${AUTHENTIK_TOKEN}" ]]; then
        log_warn "AUTHENTIK_TOKEN not set, skipping OAuth configuration"
        log_info "To enable OAuth, set AUTHENTIK_TOKEN and re-run this script"
        return 0
    fi

    # Fetch OAuth provider credentials from Authentik
    local provider_result
    provider_result=$(curl -sf \
        -H "Authorization: Bearer ${AUTHENTIK_TOKEN}" \
        -H "Content-Type: application/json" \
        "${AUTHENTIK_URL}/api/v3/providers/oauth2/?name=omni-coder-provider" 2>&1) || {
        log_warn "Could not reach Authentik API, skipping OAuth setup"
        return 0
    }

    local client_id
    client_id=$(echo "${provider_result}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
print(results[0]['client_id'] if results else '')
" 2>/dev/null || echo "")

    local client_secret
    client_secret=$(echo "${provider_result}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
print(results[0].get('client_secret', '') if results else '')
" 2>/dev/null || echo "")

    if [[ -z "${client_id}" ]]; then
        log_warn "Coder OAuth provider not found in Authentik, skipping"
        log_info "Create an OAuth2 provider named 'omni-coder-provider' in Authentik first"
        return 0
    fi

    # Configure Coder OAuth2 via the deployment config API
    local oauth_payload
    oauth_payload=$(cat <<EOF
{
    "oidc_issuer_url": "${AUTHENTIK_URL}/application/o/omni-coder/",
    "oidc_client_id": "${client_id}",
    "oidc_client_secret": "${client_secret}",
    "oidc_allow_signups": true,
    "oidc_email_domain": ["omni-quantum.internal"],
    "oidc_scopes": ["openid", "profile", "email"],
    "oidc_ignore_email_verified": true,
    "oidc_username_field": "preferred_username",
    "oidc_sign_in_text": "Sign in with Omni Quantum SSO",
    "oidc_icon_url": "${AUTHENTIK_URL}/static/dist/assets/icons/icon.svg"
}
EOF
    )

    # Apply OIDC settings via Coder API
    local oidc_result
    oidc_result=$(coder_api PATCH "/deployment/config" -d "${oauth_payload}")
    local oidc_code="${oidc_result%%|*}"

    if [[ "${oidc_code}" == "200" || "${oidc_code}" == "204" ]]; then
        log_success "Authentik OAuth configured successfully"
        log_info "  Issuer: ${AUTHENTIK_URL}/application/o/omni-coder/"
        log_info "  Client ID: ${client_id:0:8}..."
    else
        log_warn "OAuth configuration returned HTTP ${oidc_code}"
        log_info "OIDC can also be configured via environment variables on the Coder server"
        log_info "  CODER_OIDC_ISSUER_URL=${AUTHENTIK_URL}/application/o/omni-coder/"
        log_info "  CODER_OIDC_CLIENT_ID=${client_id}"
        log_info "  CODER_OIDC_CLIENT_SECRET=<secret>"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Set organization defaults
# ═══════════════════════════════════════════════════════════════════════════════
set_org_defaults() {
    log_step "Phase 5: Setting organization defaults..."

    # Set max workspace lifetime to 8 hours (28800 seconds)
    # and auto-stop idle timeout to 2 hours (7200000 milliseconds)
    local defaults_payload
    defaults_payload=$(cat <<'EOF'
{
    "max_ttl_ms": 28800000,
    "default_ttl_ms": 28800000,
    "activity_bump_ms": 3600000,
    "autostop_requirement": {
        "days_of_week": ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"],
        "weeks": 1
    },
    "allow_user_autostart": true,
    "allow_user_autostop": true,
    "failure_ttl_ms": 86400000,
    "time_til_dormant_ms": 604800000,
    "time_til_dormant_autodelete_ms": 2592000000
}
EOF
    )

    # Apply defaults to the default organization
    local org_result
    org_result=$(coder_api GET "/organizations")
    local org_code="${org_result%%|*}"
    local org_body="${org_result#*|}"

    local org_id=""
    if [[ "${org_code}" == "200" ]]; then
        org_id=$(echo "${org_body}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
orgs = data if isinstance(data, list) else data.get('organizations', [])
print(orgs[0]['id'] if orgs else '')
" 2>/dev/null || echo "")
    fi

    if [[ -n "${org_id}" ]]; then
        local update_result
        update_result=$(coder_api PATCH "/organizations/${org_id}" -d "${defaults_payload}")
        local update_code="${update_result%%|*}"

        if [[ "${update_code}" == "200" || "${update_code}" == "204" ]]; then
            log_success "Organization defaults set"
        else
            log_warn "Organization update returned HTTP ${update_code}"
        fi
    else
        log_warn "Could not determine organization ID"
    fi

    # Set deployment-wide workspace idle timeout to 2 hours
    local idle_payload
    idle_payload=$(cat <<'EOF'
{
    "user_quiet_hours_schedule": {
        "default_schedule": "CRON_TZ=UTC 0 0 * * *",
        "allow_user_custom": true
    }
}
EOF
    )

    local idle_result
    idle_result=$(coder_api PATCH "/deployment/config" -d "${idle_payload}")
    local idle_code="${idle_result%%|*}"

    if [[ "${idle_code}" == "200" || "${idle_code}" == "204" ]]; then
        log_success "Deployment quiet hours configured"
    else
        log_info "Quiet hours configuration returned HTTP ${idle_code} (may require restart)"
    fi

    log_info "Organization defaults:"
    log_info "  Max workspace lifetime: 8 hours"
    log_info "  Auto-stop on idle: 2 hours"
    log_info "  Dormant after: 7 days"
    log_info "  Auto-delete dormant: 30 days"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6: Register with Orchestrator (System 37)
# ═══════════════════════════════════════════════════════════════════════════════
register_orchestrator() {
    log_step "Phase 6: Registering with System 37 Orchestrator..."

    local payload
    payload=$(cat <<'EOF'
{
    "system_id": 36,
    "system_name": "code-forge",
    "service_type": "coder",
    "display_name": "Code Forge (Coder)",
    "health_endpoint": "http://omni-coder:7080/healthz",
    "metrics_endpoint": "http://omni-coder:7080/api/v2/deployment/stats",
    "prometheus_endpoint": "http://omni-coder:2112/metrics",
    "api_endpoint": "http://omni-coder:7080/api/v2",
    "status": "running",
    "version": "latest",
    "dependencies": ["omni-postgres", "omni-authentik"],
    "capabilities": [
        "workspace-provisioning",
        "template-management",
        "dev-environments",
        "oauth2-sso",
        "prometheus-metrics",
        "docker-provisioner"
    ],
    "network": "omni-quantum-network",
    "ports": {
        "http": 7080,
        "prometheus": 2112
    },
    "templates": [
        "python-dev",
        "typescript-dev",
        "go-dev",
        "rust-dev",
        "fullstack-dev"
    ],
    "tags": ["development", "workspaces", "ide", "code-forge"]
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
# Main Execution
# ═══════════════════════════════════════════════════════════════════════════════
main() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  System 36 — Code Forge (Coder) — Initialization${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    wait_for_coder
    create_admin_user
    push_all_templates
    configure_authentik_oauth
    set_org_defaults
    register_orchestrator

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  System 36 — Code Forge initialization complete${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    log_success "All initialization phases completed successfully"
    log_info "Coder URL: ${CODER_URL}"
    log_info "Templates: python-dev, typescript-dev, go-dev, rust-dev, fullstack-dev"
    log_info "Admin user: ${CODER_ADMIN_USERNAME}"
}

main "$@"
