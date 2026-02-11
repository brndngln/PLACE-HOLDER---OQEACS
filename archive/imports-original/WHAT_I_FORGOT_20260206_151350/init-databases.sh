#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# ⚛ OMNI QUANTUM ELITE — POSTGRESQL DATABASE CREATOR
# ═══════════════════════════════════════════════════════════════════════════════
# Creates all required PostgreSQL databases, users, grants, and extensions.
# Safe to run multiple times (idempotent).
#
# Usage:
#   ./init-databases.sh              # Create all databases
#   ./init-databases.sh --verify     # Verify all databases exist
#   ./init-databases.sh --drop       # Drop and recreate (DESTRUCTIVE!)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source .env if available
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# ─── Configuration ────────────────────────────────────────────────────────────
PG_HOST="${POSTGRES_HOST:-omni-postgres}"
PG_PORT="${POSTGRES_PORT:-5432}"
PG_SUPERUSER="${POSTGRES_SUPERUSER:-omni_admin}"
PG_SUPERUSER_PASSWORD="${POSTGRES_SUPERUSER_PASSWORD:-}"
PG_MAX_RETRIES=30
PG_RETRY_INTERVAL=2

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC}   $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERR]${NC}  $1"; }
log_section() { echo -e "\n${BOLD}${CYAN}═══ $1 ═══${NC}"; }

# ─── Parse Arguments ─────────────────────────────────────────────────────────
VERIFY_ONLY=false
DROP_FIRST=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --verify)  VERIFY_ONLY=true; shift ;;
        --drop)    DROP_FIRST=true; shift ;;
        -h|--help) echo "Usage: $0 [--verify|--drop]"; exit 0 ;;
        *)         echo "Unknown: $1"; exit 1 ;;
    esac
done

# ─── Database Definitions ────────────────────────────────────────────────────
# Format: "db_name:db_user:extensions"
DATABASES=(
    "omni_gitea:omni_gitea:uuid-ossp"
    "omni_mattermost:omni_mattermost:uuid-ossp"
    "omni_n8n:omni_n8n:uuid-ossp"
    "omni_langfuse:omni_langfuse:uuid-ossp,pgcrypto"
    "omni_authentik:omni_authentik:uuid-ossp"
    "omni_superset:omni_superset:uuid-ossp"
    "omni_calcom:omni_calcom:uuid-ossp,pgcrypto"
    "omni_woodpecker:omni_woodpecker:uuid-ossp"
    "omni_coder:omni_coder:uuid-ossp"
    "omni_plane:omni_plane:uuid-ossp,pgcrypto"
    "omni_listmonk:omni_listmonk:uuid-ossp"
    "omni_chatwoot:omni_chatwoot:uuid-ossp,pgcrypto,pg_trgm"
    "omni_posthog:omni_posthog:uuid-ossp,pgcrypto"
    "omni_glitchtip:omni_glitchtip:uuid-ossp,citext"
    "omni_unleash:omni_unleash:uuid-ossp"
    "omni_orchestrator:omni_orchestrator:uuid-ossp,pgcrypto"
    "omni_sla_tracker:omni_sla_tracker:uuid-ossp"
    "omni_backup_orchestrator:omni_backup_orchestrator:uuid-ossp"
    "omni_financial:omni_financial:uuid-ossp,pgcrypto"
)

# ─── PSQL Execution ──────────────────────────────────────────────────────────
psql_exec() {
    PGPASSWORD="${PG_SUPERUSER_PASSWORD}" psql \
        -h "$PG_HOST" \
        -p "$PG_PORT" \
        -U "$PG_SUPERUSER" \
        -d postgres \
        --no-password \
        -t -A \
        -c "$1" 2>/dev/null
}

psql_exec_db() {
    local db="$1"
    local sql="$2"
    PGPASSWORD="${PG_SUPERUSER_PASSWORD}" psql \
        -h "$PG_HOST" \
        -p "$PG_PORT" \
        -U "$PG_SUPERUSER" \
        -d "$db" \
        --no-password \
        -t -A \
        -c "$sql" 2>/dev/null
}

# ─── Wait for PostgreSQL ─────────────────────────────────────────────────────
wait_for_postgres() {
    log_info "Waiting for PostgreSQL at ${PG_HOST}:${PG_PORT}..."
    local attempt=0
    while [[ $attempt -lt $PG_MAX_RETRIES ]]; do
        if PGPASSWORD="${PG_SUPERUSER_PASSWORD}" pg_isready \
            -h "$PG_HOST" -p "$PG_PORT" -U "$PG_SUPERUSER" &>/dev/null; then
            log_success "PostgreSQL is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep "$PG_RETRY_INTERVAL"
    done
    echo ""
    log_error "PostgreSQL not available after $((PG_MAX_RETRIES * PG_RETRY_INTERVAL))s"
    exit 1
}

# ─── Get password from .env ──────────────────────────────────────────────────
get_db_password() {
    local db_name="$1"
    local var_prefix
    var_prefix=$(echo "$db_name" | sed 's/omni_//' | tr '[:lower:]' '[:upper:]')
    local var_name="${var_prefix}_DB_PASSWORD"
    echo "${!var_name:-$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 32)}"
}

# ─── Create Database ─────────────────────────────────────────────────────────
create_database() {
    local db_name="$1"
    local db_user="$2"
    local extensions="$3"
    local db_password
    db_password=$(get_db_password "$db_name")

    # Check if database exists
    local exists
    exists=$(psql_exec "SELECT 1 FROM pg_database WHERE datname = '${db_name}'" || echo "")

    if [[ "$DROP_FIRST" == "true" ]] && [[ "$exists" == "1" ]]; then
        log_warn "Dropping ${db_name}..."
        psql_exec "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${db_name}' AND pid <> pg_backend_pid();" || true
        psql_exec "DROP DATABASE IF EXISTS ${db_name};"
        exists=""
    fi

    # Create user if not exists
    local user_exists
    user_exists=$(psql_exec "SELECT 1 FROM pg_roles WHERE rolname = '${db_user}'" || echo "")
    if [[ "$user_exists" != "1" ]]; then
        psql_exec "CREATE ROLE ${db_user} WITH LOGIN PASSWORD '${db_password}';"
        log_success "  Created user: ${db_user}"
    else
        psql_exec "ALTER ROLE ${db_user} WITH PASSWORD '${db_password}';" || true
    fi

    # Create database if not exists
    if [[ "$exists" != "1" ]]; then
        psql_exec "CREATE DATABASE ${db_name} OWNER ${db_user} ENCODING 'UTF8' LC_COLLATE 'en_US.utf8' LC_CTYPE 'en_US.utf8' TEMPLATE template0;" 2>/dev/null || \
        psql_exec "CREATE DATABASE ${db_name} OWNER ${db_user} ENCODING 'UTF8';"
        log_success "  Created database: ${db_name}"
    else
        log_info "  Database exists: ${db_name}"
    fi

    # Grant privileges
    psql_exec "GRANT ALL PRIVILEGES ON DATABASE ${db_name} TO ${db_user};"
    psql_exec_db "$db_name" "GRANT ALL ON SCHEMA public TO ${db_user};" || true
    psql_exec_db "$db_name" "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${db_user};" || true
    psql_exec_db "$db_name" "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${db_user};" || true

    # Create extensions
    IFS=',' read -ra EXTS <<< "$extensions"
    for ext in "${EXTS[@]}"; do
        ext=$(echo "$ext" | xargs)  # trim whitespace
        if [[ -n "$ext" ]]; then
            psql_exec_db "$db_name" "CREATE EXTENSION IF NOT EXISTS \"${ext}\";" || \
                log_warn "  Extension ${ext} not available for ${db_name}"
        fi
    done
}

# ─── Verify Database ─────────────────────────────────────────────────────────
verify_database() {
    local db_name="$1"
    local db_user="$2"
    local extensions="$3"

    local exists
    exists=$(psql_exec "SELECT 1 FROM pg_database WHERE datname = '${db_name}'" || echo "")

    if [[ "$exists" == "1" ]]; then
        # Check connectivity
        local can_connect
        can_connect=$(psql_exec_db "$db_name" "SELECT 1;" || echo "0")
        if [[ "$can_connect" == "1" ]]; then
            # Count extensions
            local ext_count
            ext_count=$(psql_exec_db "$db_name" "SELECT COUNT(*) FROM pg_extension WHERE extname NOT IN ('plpgsql');" || echo "0")
            log_success "  ✓ ${db_name} (user: ${db_user}, extensions: ${ext_count})"
        else
            log_error "  ✗ ${db_name} — cannot connect"
        fi
    else
        log_error "  ✗ ${db_name} — does not exist"
    fi
}

# ─── Orchestrator Schema ─────────────────────────────────────────────────────
create_orchestrator_schema() {
    log_section "ORCHESTRATOR SCHEMA"

    psql_exec_db "omni_orchestrator" "
    CREATE TABLE IF NOT EXISTS platform_events (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        event_type VARCHAR(100) NOT NULL,
        source_system VARCHAR(100) NOT NULL,
        severity VARCHAR(20) DEFAULT 'info',
        title VARCHAR(500) NOT NULL,
        details JSONB DEFAULT '{}',
        acknowledged BOOLEAN DEFAULT false,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_events_type ON platform_events(event_type);
    CREATE INDEX IF NOT EXISTS idx_events_created ON platform_events(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_events_severity ON platform_events(severity);

    CREATE TABLE IF NOT EXISTS service_health_log (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        service_id VARCHAR(50) NOT NULL,
        status VARCHAR(20) NOT NULL,
        response_time_ms INTEGER,
        details JSONB DEFAULT '{}',
        checked_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_health_service ON service_health_log(service_id, checked_at DESC);

    CREATE TABLE IF NOT EXISTS pipeline_runs (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        project_id VARCHAR(100),
        pipeline_type VARCHAR(50) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        stage VARCHAR(50),
        started_at TIMESTAMPTZ DEFAULT NOW(),
        completed_at TIMESTAMPTZ,
        duration_seconds INTEGER,
        result JSONB DEFAULT '{}',
        scores JSONB DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_pipeline_project ON pipeline_runs(project_id);
    CREATE INDEX IF NOT EXISTS idx_pipeline_status ON pipeline_runs(status);

    CREATE TABLE IF NOT EXISTS agent_handoffs (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        pipeline_run_id UUID REFERENCES pipeline_runs(id),
        from_agent VARCHAR(50),
        to_agent VARCHAR(50),
        handoff_data JSONB DEFAULT '{}',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS knowledge_stats (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        collection_name VARCHAR(100) NOT NULL,
        vector_count BIGINT DEFAULT 0,
        last_updated TIMESTAMPTZ DEFAULT NOW(),
        metadata JSONB DEFAULT '{}'
    );
    " || log_warn "Some orchestrator schema tables may already exist"

    log_success "Orchestrator schema initialized"
}

# ─── Financial Services Schema ────────────────────────────────────────────────
create_financial_schema() {
    log_section "FINANCIAL SERVICES SCHEMA"

    psql_exec_db "omni_financial" "
    CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";
    CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";

    CREATE TABLE IF NOT EXISTS organizations (
        id VARCHAR(50) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        status VARCHAR(20) DEFAULT 'ACTIVE',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS businesses (
        id VARCHAR(50) PRIMARY KEY,
        parent_id VARCHAR(50) REFERENCES organizations(id),
        name VARCHAR(255) NOT NULL,
        status VARCHAR(20) DEFAULT 'ACTIVE',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS bank_accounts (
        id VARCHAR(50) PRIMARY KEY,
        org_id VARCHAR(50) REFERENCES organizations(id),
        account_name VARCHAR(255),
        provider VARCHAR(50),
        account_type VARCHAR(50),
        cached_balance DECIMAL(15,2) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS transactions (
        id VARCHAR(50) PRIMARY KEY,
        org_id VARCHAR(50) REFERENCES organizations(id),
        business_id VARCHAR(50) REFERENCES businesses(id),
        transaction_type VARCHAR(20),
        category VARCHAR(100),
        amount DECIMAL(15,2),
        description TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_txn_org ON transactions(org_id);
    CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(created_at DESC);

    CREATE TABLE IF NOT EXISTS tax_reserves (
        id VARCHAR(50) PRIMARY KEY,
        org_id VARCHAR(50) REFERENCES organizations(id),
        business_id VARCHAR(50) REFERENCES businesses(id),
        tax_year INTEGER,
        quarter INTEGER,
        due_date DATE,
        required_amount DECIMAL(15,2) DEFAULT 0,
        reserved_amount DECIMAL(15,2) DEFAULT 0,
        paid_amount DECIMAL(15,2) DEFAULT 0,
        status VARCHAR(20) DEFAULT 'UNDERFUNDED',
        payment_status VARCHAR(20) DEFAULT 'NOT_DUE',
        federal_portion DECIMAL(15,2) DEFAULT 0,
        state_portion DECIMAL(15,2) DEFAULT 0,
        se_tax_portion DECIMAL(15,2) DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS invoices (
        id VARCHAR(50) PRIMARY KEY,
        org_id VARCHAR(50) REFERENCES organizations(id),
        client_name VARCHAR(255),
        project_id VARCHAR(100),
        amount DECIMAL(15,2),
        status VARCHAR(20) DEFAULT 'DRAFT',
        due_date DATE,
        issued_at TIMESTAMPTZ,
        paid_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_invoice_status ON invoices(status);

    CREATE TABLE IF NOT EXISTS contractors (
        id VARCHAR(50) PRIMARY KEY,
        org_id VARCHAR(50) REFERENCES organizations(id),
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255),
        rate_type VARCHAR(20) DEFAULT 'hourly',
        rate DECIMAL(10,2),
        status VARCHAR(20) DEFAULT 'ACTIVE',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS alerts (
        id VARCHAR(50) PRIMARY KEY,
        org_id VARCHAR(50),
        severity VARCHAR(20),
        category VARCHAR(50),
        alert_type VARCHAR(100),
        title VARCHAR(500),
        message TEXT,
        details JSONB DEFAULT '{}',
        status VARCHAR(20) DEFAULT 'NEW',
        fingerprint VARCHAR(64),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        resolved_at TIMESTAMPTZ
    );
    CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
    CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
    " || log_warn "Some financial schema tables may already exist"

    log_success "Financial services schema initialized"
}

# ─── SLA Tracker Schema ──────────────────────────────────────────────────────
create_sla_schema() {
    log_section "SLA TRACKER SCHEMA"

    psql_exec_db "omni_sla_tracker" "
    CREATE TABLE IF NOT EXISTS sla_definitions (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        service_name VARCHAR(100) NOT NULL UNIQUE,
        target_uptime DECIMAL(5,3) DEFAULT 99.900,
        max_response_time_ms INTEGER DEFAULT 5000,
        max_error_rate DECIMAL(5,3) DEFAULT 1.000,
        evaluation_window VARCHAR(20) DEFAULT '30d',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS sla_measurements (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        service_name VARCHAR(100) NOT NULL,
        measured_uptime DECIMAL(8,5),
        avg_response_time_ms INTEGER,
        error_rate DECIMAL(8,5),
        is_compliant BOOLEAN DEFAULT true,
        period_start TIMESTAMPTZ,
        period_end TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_sla_service ON sla_measurements(service_name, created_at DESC);

    CREATE TABLE IF NOT EXISTS sla_violations (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        service_name VARCHAR(100) NOT NULL,
        violation_type VARCHAR(50) NOT NULL,
        threshold DECIMAL(10,5),
        actual_value DECIMAL(10,5),
        duration_seconds INTEGER,
        acknowledged BOOLEAN DEFAULT false,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    " || log_warn "Some SLA schema tables may already exist"

    log_success "SLA tracker schema initialized"
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

echo -e "${BOLD}${CYAN}"
echo "  ⚛  OMNI QUANTUM ELITE — Database Initializer"
echo "  ─────────────────────────────────────────────────"
echo -e "${NC}"

wait_for_postgres

if [[ "$VERIFY_ONLY" == "true" ]]; then
    log_section "VERIFYING ALL DATABASES"
    total=0
    ok=0
    for entry in "${DATABASES[@]}"; do
        IFS=':' read -r db_name db_user extensions <<< "$entry"
        verify_database "$db_name" "$db_user" "$extensions"
        total=$((total + 1))
    done
    echo ""
    log_info "Verified ${total} databases"
    exit 0
fi

log_section "CREATING DATABASES AND USERS"

created=0
skipped=0
for entry in "${DATABASES[@]}"; do
    IFS=':' read -r db_name db_user extensions <<< "$entry"
    log_info "Processing: ${db_name}"
    create_database "$db_name" "$db_user" "$extensions"
    created=$((created + 1))
done

# Create application-specific schemas
create_orchestrator_schema
create_financial_schema
create_sla_schema

# ─── PostgreSQL Tuning ────────────────────────────────────────────────────────
log_section "POSTGRESQL CONFIGURATION"
log_info "Setting recommended parameters..."

psql_exec "ALTER SYSTEM SET shared_buffers = '256MB';" || true
psql_exec "ALTER SYSTEM SET effective_cache_size = '1GB';" || true
psql_exec "ALTER SYSTEM SET work_mem = '16MB';" || true
psql_exec "ALTER SYSTEM SET maintenance_work_mem = '128MB';" || true
psql_exec "ALTER SYSTEM SET max_connections = '200';" || true
psql_exec "ALTER SYSTEM SET log_min_duration_statement = '1000';" || true
psql_exec "ALTER SYSTEM SET log_statement = 'ddl';" || true
psql_exec "ALTER SYSTEM SET log_line_prefix = '%t [%p] %q%u@%d ';" || true

log_success "PostgreSQL tuning applied (requires restart for shared_buffers)"

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}  ⚛  Database initialization complete!${NC}"
echo -e "     ${GREEN}${created} databases created/verified${NC}"
echo -e "     ${GREEN}3 application schemas initialized${NC}"
echo ""
echo -e "  Next: Run ${CYAN}scripts/boot-platform.sh${NC} to start all services"
echo ""
