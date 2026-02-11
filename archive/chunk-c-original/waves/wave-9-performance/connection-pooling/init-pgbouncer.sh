#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  PGBOUNCER INIT — Validate and test connection pooling                             ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "${GREEN}[PGBOUNCER]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
pass() { echo -e "${GREEN}✅ PASS${NC} $*"; }
fail() { echo -e "${RED}❌ FAIL${NC} $*"; }

PGBOUNCER_HOST="${PGBOUNCER_HOST:-omni-pgbouncer}"
PGBOUNCER_PORT="${PGBOUNCER_PORT:-6432}"
PGBOUNCER_ADMIN_USER="${PGBOUNCER_ADMIN_USER:-pgbouncer_admin}"
PGBOUNCER_ADMIN_PASS="${PGBOUNCER_ADMIN_PASS:-adminpass}"

DB_USER="${DB_USER:-fortress}"
DB_PASS="${DB_PASS:-quantum_elite_2024}"
DB_NAME="${DB_NAME:-financial_fortress}"

log "Waiting for PgBouncer to be ready..."
for i in {1..30}; do
    if pg_isready -h "$PGBOUNCER_HOST" -p "$PGBOUNCER_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
        pass "PgBouncer is accepting connections"
        break
    fi
    sleep 1
done

# Test connection through PgBouncer
log "Testing database connection through PgBouncer..."
if PGPASSWORD="$DB_PASS" psql -h "$PGBOUNCER_HOST" -p "$PGBOUNCER_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1 AS test;" > /dev/null 2>&1; then
    pass "Database connection through PgBouncer successful"
else
    fail "Database connection through PgBouncer failed"
    exit 1
fi

# Show pool stats
log "Fetching PgBouncer statistics..."
PGPASSWORD="$PGBOUNCER_ADMIN_PASS" psql -h "$PGBOUNCER_HOST" -p "$PGBOUNCER_PORT" -U "$PGBOUNCER_ADMIN_USER" -d pgbouncer << 'EOF' || true
SHOW POOLS;
SHOW STATS;
SHOW CONFIG;
EOF

log "PgBouncer initialization complete"
