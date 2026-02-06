#!/bin/bash
# DATABASE MIGRATION RUNNER — OMNI QUANTUM ELITE v3.0
set -euo pipefail
MIGRATIONS_DIR="${MIGRATIONS_DIR:-./migrations}"
DATABASE_URL="${DATABASE_URL:-postgresql://fortress:quantum_elite_2024@omni-postgres:5432/financial_fortress}"
echo "Running migrations from $MIGRATIONS_DIR..."
for f in $(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort); do
    echo "Applying: $(basename $f)"
    psql "$DATABASE_URL" -f "$f"
done
echo "Migrations complete"
