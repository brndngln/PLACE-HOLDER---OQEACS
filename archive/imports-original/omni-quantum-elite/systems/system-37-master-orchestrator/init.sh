#!/bin/bash
###############################################################################
# System 37 — Master Orchestrator Init Script
# Sets up database, installs CLI, builds images, starts services.
###############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   ⚛  OMNI COMMAND — Master Orchestrator  ║"
echo "  ║          System 37 Initialization         ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"

# --- 1. Create PostgreSQL database ---
echo -e "${BLUE}[1/5] Creating PostgreSQL database...${NC}"
docker exec omni-postgres psql -U postgres -c "
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'omni_orchestrator') THEN
      CREATE ROLE omni_orchestrator WITH LOGIN PASSWORD '${ORCHESTRATOR_DB_PASSWORD:-orchestrator_secret}';
    END IF;
  END
  \$\$;
  SELECT 'CREATE DATABASE omni_orchestrator OWNER omni_orchestrator'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'omni_orchestrator')\gexec
" 2>/dev/null || echo "  Database may already exist — OK"
echo -e "${GREEN}  ✓ PostgreSQL ready${NC}"

# --- 2. Build custom images ---
echo -e "${BLUE}[2/5] Building orchestrator images...${NC}"
cd "$SCRIPT_DIR"
docker compose build --quiet
echo -e "${GREEN}  ✓ Images built${NC}"

# --- 3. Start services ---
echo -e "${BLUE}[3/5] Starting orchestrator services...${NC}"
docker compose up -d
echo -e "${GREEN}  ✓ Services starting${NC}"

# --- 4. Install CLI tool ---
echo -e "${BLUE}[4/5] Installing 'omni' CLI...${NC}"
if [ -f "$SCRIPT_DIR/cli/omni.py" ]; then
    chmod +x "$SCRIPT_DIR/cli/omni.py"
    mkdir -p /usr/local/bin 2>/dev/null || true
    cp "$SCRIPT_DIR/cli/omni.py" /usr/local/bin/omni 2>/dev/null || \
    ln -sf "$SCRIPT_DIR/cli/omni.py" ~/omni 2>/dev/null || true
    echo -e "${GREEN}  ✓ CLI installed (run: omni status)${NC}"
else
    echo "  ⚠ CLI not found — skipping"
fi

# --- 5. Wait for orchestrator to be healthy ---
echo -e "${BLUE}[5/5] Waiting for orchestrator to be healthy...${NC}"
for i in $(seq 1 30); do
    if curl -sf http://localhost:9500/health >/dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Orchestrator is healthy!${NC}"
        break
    fi
    sleep 2
done

# --- Summary ---
echo ""
echo -e "${PURPLE}  ══════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ System 37 — Master Orchestrator is LIVE${NC}"
echo ""
echo "  Endpoints:"
echo "    API:       http://localhost:9500"
echo "    Dashboard: http://localhost:9501"
echo "    Voice:     http://localhost:9502"
echo "    API Docs:  http://localhost:9500/docs"
echo "    Metrics:   http://localhost:9500/metrics"
echo ""
echo "  CLI Commands:"
echo "    omni status         — Platform overview"
echo "    omni services       — All services"
echo "    omni health <svc>   — Check service"
echo "    omni restart <svc>  — Restart container"
echo "    omni help           — All commands"
echo ""
echo "  ChatOps:  Type '!omni help' in Mattermost #omni-control"
echo "  Voice:    Say 'check platform status' to Omi"
echo -e "${PURPLE}  ══════════════════════════════════════════${NC}"
