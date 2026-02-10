#!/usr/bin/env bash
###############################################################################
# setup-database-engines.sh - Configure dynamic database credentials
#
# System 2: Cryptographic Fortress
#
# Sets up the Vault database secrets engine with PostgreSQL connections for
# each service. Creates readonly (SELECT, 1h TTL) and readwrite (ALL, 4h TTL)
# roles per database.
###############################################################################
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
export VAULT_ADDR

PG_HOST="${PG_HOST:-omni-postgresql}"
PG_PORT="${PG_PORT:-5432}"
PG_ADMIN_USER="${PG_ADMIN_USER:-postgres}"
PG_ADMIN_PASSWORD="${PG_ADMIN_PASSWORD:-}"
PG_SSL_MODE="${PG_SSL_MODE:-require}"

# All services with PostgreSQL databases
DB_SERVICES=(
    gitea
    authentik
    langfuse
    plane
    wikijs
    superset
    calcom
    twenty
    crater
    mattermost
    n8n
    keycloak
    glitchtip
    listmonk
    chatwoot
    pact-broker
    mlflow
    formbricks
    tolgee
    woodpecker
)

# Readonly role TTL
READONLY_TTL="1h"
READONLY_MAX_TTL="2h"

# Readwrite role TTL
READWRITE_TTL="4h"
READWRITE_MAX_TTL="8h"

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
        log_error "setup-database-engines.sh exited with code $exit_code"
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

    if [[ -z "$PG_ADMIN_PASSWORD" ]]; then
        log_error "PG_ADMIN_PASSWORD is not set. Provide the PostgreSQL admin password."
        return 1
    fi

    # Verify database engine is mounted
    if ! vault secrets list -format=json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'database/' in d else 1)" 2>/dev/null; then
        log_error "Database secrets engine not mounted at database/. Run vault-init.sh first."
        return 1
    fi

    log_ok "Prerequisites validated"
}

# ---------------------------------------------------------------------------
# Convert service name to DB name (handle hyphens)
# ---------------------------------------------------------------------------
service_to_dbname() {
    local service="$1"
    echo "${service//-/_}"
}

# ---------------------------------------------------------------------------
# Configure a database connection
# ---------------------------------------------------------------------------
configure_db_connection() {
    local service="$1"
    local db_name
    db_name=$(service_to_dbname "$service")

    log_info "Configuring database connection for: ${service} (db: ${db_name})"

    local connection_url="postgresql://{{username}}:{{password}}@${PG_HOST}:${PG_PORT}/${db_name}?sslmode=${PG_SSL_MODE}"

    vault write "database/config/${service}" \
        plugin_name=postgresql-database-plugin \
        allowed_roles="${service}-readonly,${service}-readwrite" \
        connection_url="$connection_url" \
        username="$PG_ADMIN_USER" \
        password="$PG_ADMIN_PASSWORD" \
        max_open_connections=5 \
        max_idle_connections=2 \
        max_connection_lifetime="30m"

    log_ok "Database connection configured: ${service}"
}

# ---------------------------------------------------------------------------
# Create readonly role
# ---------------------------------------------------------------------------
create_readonly_role() {
    local service="$1"
    local db_name
    db_name=$(service_to_dbname "$service")

    log_info "Creating readonly role: ${service}-readonly"

    local creation_sql
    creation_sql=$(cat <<EOSQL
CREATE ROLE "{{name}}" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{{name}}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "{{name}}";
EOSQL
    )

    local revocation_sql
    revocation_sql=$(cat <<EOSQL
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM "{{name}}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM "{{name}}";
DROP ROLE IF EXISTS "{{name}}";
EOSQL
    )

    vault write "database/roles/${service}-readonly" \
        db_name="$service" \
        creation_statements="$creation_sql" \
        revocation_statements="$revocation_sql" \
        default_ttl="$READONLY_TTL" \
        max_ttl="$READONLY_MAX_TTL"

    log_ok "Readonly role created: ${service}-readonly (TTL: ${READONLY_TTL})"
}

# ---------------------------------------------------------------------------
# Create readwrite role
# ---------------------------------------------------------------------------
create_readwrite_role() {
    local service="$1"
    local db_name
    db_name=$(service_to_dbname "$service")

    log_info "Creating readwrite role: ${service}-readwrite"

    local creation_sql
    creation_sql=$(cat <<EOSQL
CREATE ROLE "{{name}}" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{{name}}";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{{name}}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{{name}}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "{{name}}";
EOSQL
    )

    local revocation_sql
    revocation_sql=$(cat <<EOSQL
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM "{{name}}";
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM "{{name}}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM "{{name}}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM "{{name}}";
DROP ROLE IF EXISTS "{{name}}";
EOSQL
    )

    vault write "database/roles/${service}-readwrite" \
        db_name="$service" \
        creation_statements="$creation_sql" \
        revocation_statements="$revocation_sql" \
        default_ttl="$READWRITE_TTL" \
        max_ttl="$READWRITE_MAX_TTL"

    log_ok "Readwrite role created: ${service}-readwrite (TTL: ${READWRITE_TTL})"
}

# ---------------------------------------------------------------------------
# Test credential generation
# ---------------------------------------------------------------------------
test_credential_generation() {
    local service="$1"
    local role_type="$2"
    local role_name="${service}-${role_type}"

    log_info "Testing credential generation: ${role_name}"

    local result
    if result=$(vault read -format=json "database/creds/${role_name}" 2>&1); then
        local username
        local lease_duration
        username=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['username'])" 2>/dev/null)
        lease_duration=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['lease_duration'])" 2>/dev/null)
        log_ok "Generated creds for ${role_name}: user=${username}, lease=${lease_duration}s"

        # Immediately revoke the test credentials
        local lease_id
        lease_id=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin)['lease_id'])" 2>/dev/null)
        if [[ -n "$lease_id" ]]; then
            vault lease revoke "$lease_id" &>/dev/null || true
            log_info "Revoked test lease: ${lease_id}"
        fi
        return 0
    else
        log_warn "Could not generate test creds for ${role_name}: ${result}"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Setup single service
# ---------------------------------------------------------------------------
setup_service() {
    local service="$1"

    log_step "Setting up database engine for: ${service}"

    configure_db_connection "$service"
    create_readonly_role "$service"
    create_readwrite_role "$service"
}

# ---------------------------------------------------------------------------
# Output summary
# ---------------------------------------------------------------------------
output_summary() {
    local total_services="${#DB_SERVICES[@]}"
    local total_roles=$((total_services * 2))

    echo ""
    echo "======================================================================"
    echo " Dynamic Database Credentials Summary"
    echo "======================================================================"
    echo ""
    log_info "Total services configured: ${total_services}"
    log_info "Total roles created: ${total_roles}"
    echo ""
    echo "  Readonly roles  (${READONLY_TTL} TTL):  ${total_services}"
    echo "  Readwrite roles (${READWRITE_TTL} TTL):  ${total_services}"
    echo ""

    printf "  %-20s %-25s %-25s\n" "SERVICE" "READONLY ROLE" "READWRITE ROLE"
    printf "  %-20s %-25s %-25s\n" "-------" "-------------" "--------------"
    for service in "${DB_SERVICES[@]}"; do
        printf "  %-20s %-25s %-25s\n" "$service" "${service}-readonly" "${service}-readwrite"
    done

    echo ""
    echo "  Usage: vault read database/creds/{service}-{readonly|readwrite}"
    echo ""
    echo "======================================================================"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo "======================================================================"
    echo " Omni-Quantum Elite: Dynamic Database Credentials Setup"
    echo " PostgreSQL Host: ${PG_HOST}:${PG_PORT}"
    echo "======================================================================"
    echo ""

    validate_prereqs

    local configured=0
    local failed=0
    local test_passed=0
    local test_failed=0

    for service in "${DB_SERVICES[@]}"; do
        if setup_service "$service"; then
            configured=$((configured + 1))
        else
            log_error "Failed to configure: ${service}"
            failed=$((failed + 1))
        fi
    done

    echo ""
    log_step "Testing credential generation (sampling first 3 services)..."

    local test_count=0
    for service in "${DB_SERVICES[@]}"; do
        if [[ $test_count -ge 3 ]]; then
            break
        fi

        for role_type in readonly readwrite; do
            if test_credential_generation "$service" "$role_type"; then
                test_passed=$((test_passed + 1))
            else
                test_failed=$((test_failed + 1))
            fi
        done

        test_count=$((test_count + 1))
    done

    echo ""
    log_info "Configuration: ${configured} succeeded, ${failed} failed"
    log_info "Test generation: ${test_passed} passed, ${test_failed} failed"

    output_summary

    if [[ $failed -gt 0 || $test_failed -gt 0 ]]; then
        log_warn "Some operations had failures -- review output above"
        exit 1
    fi

    log_ok "All database engines configured successfully"
}

main "$@"
