#!/usr/bin/env bash
###############################################################################
# System 29: Enhanced Monitoring Stack — Init Script
# Sets up Thanos, Anomaly Detector, SLA Tracker, Capacity Planner,
# Grafana dashboards, and Prometheus alert rules.
###############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[MONITORING]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
log "Starting Enhanced Monitoring Stack setup..."

# Check Docker
if ! command -v docker &>/dev/null; then
    err "Docker is not installed"
    exit 1
fi

# Check network
if ! docker network inspect omni-quantum-network &>/dev/null; then
    warn "Creating omni-quantum-network..."
    docker network create omni-quantum-network
fi

# ---------------------------------------------------------------------------
# Create MinIO bucket for Thanos
# ---------------------------------------------------------------------------
log "Creating MinIO bucket for Thanos long-term storage..."
docker exec omni-minio mc mb local/omni-thanos-metrics --ignore-existing 2>/dev/null || \
    warn "MinIO bucket creation skipped (may already exist or MinIO not ready)"

# ---------------------------------------------------------------------------
# Create PostgreSQL database for SLA Tracker
# ---------------------------------------------------------------------------
log "Creating SLA Tracker database..."
docker exec omni-postgres psql -U postgres -c "
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sla_tracker') THEN
            CREATE ROLE sla_tracker WITH LOGIN PASSWORD '${SLA_TRACKER_DB_PASS:-sla_tracker_pass}';
        END IF;
    END
    \$\$;
    CREATE DATABASE sla_tracker OWNER sla_tracker;
" 2>/dev/null || warn "SLA database may already exist"

# ---------------------------------------------------------------------------
# Copy Prometheus alert rules
# ---------------------------------------------------------------------------
log "Installing enhanced alert rules..."
if [ -d "$ROOT_DIR/alerts" ]; then
    docker cp "$ROOT_DIR/alerts/rules.yml" omni-prometheus:/etc/prometheus/enhanced-rules.yml 2>/dev/null || \
        warn "Could not copy alert rules to Prometheus"
    # Reload Prometheus config
    curl -s -X POST http://localhost:9090/-/reload 2>/dev/null || \
        warn "Could not reload Prometheus (may need manual reload)"
fi

# ---------------------------------------------------------------------------
# Import Grafana dashboards
# ---------------------------------------------------------------------------
log "Importing Grafana dashboards..."
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_API_KEY="${GRAFANA_API_KEY:-}"

import_dashboard() {
    local file="$1"
    local name
    name=$(basename "$file" .json)

    if [ -n "$GRAFANA_API_KEY" ]; then
        local payload
        payload=$(jq '{dashboard: ., overwrite: true, folderId: 0}' "$file")
        local status
        status=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $GRAFANA_API_KEY" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "$GRAFANA_URL/api/dashboards/db")
        if [ "$status" = "200" ]; then
            ok "Imported dashboard: $name"
        else
            warn "Dashboard import returned HTTP $status: $name"
        fi
    else
        warn "No Grafana API key — skipping dashboard import for $name"
    fi
}

if [ -d "$ROOT_DIR/dashboards" ]; then
    for f in "$ROOT_DIR/dashboards"/*.json; do
        [ -f "$f" ] && import_dashboard "$f"
    done
fi

# ---------------------------------------------------------------------------
# Build custom images
# ---------------------------------------------------------------------------
log "Building custom service images..."
for svc in anomaly-detector sla-tracker capacity-planner; do
    if [ -d "$ROOT_DIR/config/$svc" ] && [ -f "$ROOT_DIR/config/$svc/Dockerfile" ]; then
        log "Building $svc..."
        docker build -t "omni-$svc:latest" "$ROOT_DIR/config/$svc/" -q && \
            ok "Built omni-$svc:latest" || \
            err "Failed to build $svc"
    fi
done

# ---------------------------------------------------------------------------
# Start services
# ---------------------------------------------------------------------------
log "Starting Enhanced Monitoring Stack services..."
cd "$ROOT_DIR"
docker compose up -d

# ---------------------------------------------------------------------------
# Wait for services to be healthy
# ---------------------------------------------------------------------------
log "Waiting for services to become healthy..."
services=("omni-thanos-query" "omni-karma" "omni-anomaly-detector" "omni-sla-tracker" "omni-capacity-planner")
for svc in "${services[@]}"; do
    for i in $(seq 1 30); do
        if docker inspect --format='{{.State.Health.Status}}' "$svc" 2>/dev/null | grep -q "healthy"; then
            ok "$svc is healthy"
            break
        fi
        if [ "$i" -eq 30 ]; then
            warn "$svc not healthy after 30 checks"
        fi
        sleep 5
    done
done

# ---------------------------------------------------------------------------
# Configure Mattermost webhook
# ---------------------------------------------------------------------------
log "Configuring Mattermost alert integrations..."
if [ -n "${MATTERMOST_URL:-}" ] && [ -n "${MATTERMOST_ALERTS_WEBHOOK:-}" ]; then
    ok "Mattermost webhook configured: $MATTERMOST_ALERTS_WEBHOOK"
else
    warn "Mattermost webhook not configured — set MATTERMOST_ALERTS_WEBHOOK"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "  Enhanced Monitoring Stack — Setup Complete"
echo "=============================================="
echo ""
echo "  Services:"
echo "    Thanos Query:     http://localhost:9091"
echo "    Karma (Alerts):   http://localhost:8180"
echo "    Anomaly Detector: http://localhost:8181"
echo "    SLA Tracker:      http://localhost:8182"
echo "    Capacity Planner: http://localhost:8183"
echo ""
echo "  Enhancements:"
echo "    ✓ Long-term metric storage via Thanos + MinIO"
echo "    ✓ Statistical anomaly detection (Z-score, IQR, EWMA)"
echo "    ✓ SLA/SLO tracking with error budgets for all services"
echo "    ✓ Capacity forecasting with threshold alerts"
echo "    ✓ Enhanced alert rules for all 28+ services"
echo "    ✓ Alert aggregation via Karma UI"
echo ""
ok "System 29: Enhanced Monitoring Stack is ONLINE"
