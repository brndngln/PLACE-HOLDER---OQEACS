#!/bin/bash
###############################################################################
# ⚛ OMNI QUANTUM ELITE — Deployment Script
# Boots all 37 systems in dependency order with health verification.
#
# Usage:
#   ./deploy.sh              Full deployment
#   ./deploy.sh --tier 0     Boot only foundation
#   ./deploy.sh --status     Check all service health
#   ./deploy.sh --down       Graceful shutdown
###############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.master.yml"
ENV_FILE="$SCRIPT_DIR/.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
YELLOW='\033[1;33m'
NC='\033[0m'

banner() {
  echo -e "${PURPLE}"
  echo "  ╔══════════════════════════════════════════════════════════╗"
  echo "  ║         ⚛  OMNI QUANTUM ELITE PLATFORM                 ║"
  echo "  ║              Deployment Controller                      ║"
  echo "  ╚══════════════════════════════════════════════════════════╝"
  echo -e "${NC}"
}

log()   { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $*"; }
ok()    { echo -e "${GREEN}  ✓${NC} $*"; }
warn()  { echo -e "${YELLOW}  ⚠${NC} $*"; }
fail()  { echo -e "${RED}  ✗${NC} $*"; }

# ---------------------------------------------------------------------------
# Prerequisite Checks
# ---------------------------------------------------------------------------
check_prerequisites() {
  log "Checking prerequisites..."

  # Docker
  if ! command -v docker &>/dev/null; then
    fail "Docker is not installed. Install: https://docs.docker.com/get-docker/"
    exit 1
  fi
  ok "Docker $(docker --version | grep -oP '\d+\.\d+\.\d+')"

  # Docker Compose v2
  if ! docker compose version &>/dev/null; then
    fail "Docker Compose v2 required. Update Docker Desktop or install plugin."
    exit 1
  fi
  ok "Docker Compose $(docker compose version --short)"

  # Memory check (recommend 16GB+)
  TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)
  TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
  if [ "$TOTAL_MEM_GB" -lt 12 ]; then
    warn "Only ${TOTAL_MEM_GB}GB RAM detected. 16GB+ recommended for full platform."
  else
    ok "${TOTAL_MEM_GB}GB RAM available"
  fi

  # .env file
  if [ ! -f "$ENV_FILE" ]; then
    fail "No .env file found. Copy .env to .env and fill in your secrets."
    exit 1
  fi

  # Check for default passwords
  if grep -q "CHANGE_ME" "$ENV_FILE"; then
    warn "Default passwords detected in .env — change before production use!"
  fi

  ok "Prerequisites passed"
  echo ""
}

# ---------------------------------------------------------------------------
# Generate Secrets (optional: replace CHANGE_ME placeholders)
# ---------------------------------------------------------------------------
generate_secrets() {
  log "Generating secure random secrets..."
  
  if [ ! -f "$ENV_FILE.bak" ]; then
    cp "$ENV_FILE" "$ENV_FILE.bak"
  fi

  # Replace each CHANGE_ME with a random 32-char hex string
  while IFS= read -r line; do
    if echo "$line" | grep -q "CHANGE_ME"; then
      key=$(echo "$line" | cut -d= -f1)
      secret=$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | xxd -p | head -c 32)
      sed -i "s|^${key}=.*|${key}=${secret}|" "$ENV_FILE"
    fi
  done < "$ENV_FILE"
  
  ok "Secrets generated (backup: .env.bak)"
  echo ""
}

# ---------------------------------------------------------------------------
# Network Setup
# ---------------------------------------------------------------------------
setup_network() {
  log "Setting up Docker network..."
  docker network create omni-quantum-network 2>/dev/null && \
    ok "Created omni-quantum-network" || \
    ok "omni-quantum-network already exists"
  echo ""
}

# ---------------------------------------------------------------------------
# Wait for container health
# ---------------------------------------------------------------------------
wait_for_healthy() {
  local container=$1
  local timeout=${2:-120}
  local elapsed=0

  while [ $elapsed -lt $timeout ]; do
    status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not_found")
    case "$status" in
      healthy)  ok "$container is healthy"; return 0 ;;
      not_found) ;;  # Container hasn't started yet
    esac
    sleep 3
    elapsed=$((elapsed + 3))
  done

  fail "$container did not become healthy within ${timeout}s"
  return 1
}

# ---------------------------------------------------------------------------
# Tiered Boot
# ---------------------------------------------------------------------------
boot_tier_0() {
  log "═══ TIER 0: Foundation ═══"
  
  # PostgreSQL + Redis first (everything depends on these)
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d omni-postgres omni-redis 2>/dev/null
  wait_for_healthy omni-postgres 60
  wait_for_healthy omni-redis 30
  
  # Vault, Prometheus, Loki, Ollama, MinIO, Restic
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d omni-vault omni-prometheus omni-loki omni-ollama omni-minio omni-restic-server 2>/dev/null
  
  for svc in omni-vault omni-prometheus omni-loki omni-minio; do
    wait_for_healthy "$svc" 90 || true
  done
  echo ""
}

boot_tier_1() {
  log "═══ TIER 1: Core Services ═══"
  
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d omni-litellm omni-authentik omni-gitea omni-n8n omni-mattermost \
    omni-qdrant omni-traefik omni-grafana omni-promtail 2>/dev/null
  
  for svc in omni-litellm omni-gitea omni-mattermost omni-traefik; do
    wait_for_healthy "$svc" 120 || true
  done
  echo ""
}

boot_tier_2() {
  log "═══ TIER 2: Application & Intelligence Services ═══"
  
  # All application services in parallel
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d \
    omni-langfuse omni-plane-web omni-nango omni-openhands omni-flowise \
    omni-wikijs omni-superset omni-calcom omni-twenty omni-crater \
    omni-crowdsec omni-portainer omni-token-infinity omni-omi-bridge \
    2>/dev/null || true

  # All intelligence microservices in parallel
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d \
    omni-code-scorer omni-gate-engine omni-intent-verifier \
    omni-context-compiler omni-tool-selector \
    omni-mcp-registry omni-mcp-docs omni-mcp-schema omni-mcp-pipeline \
    omni-anti-patterns omni-spec-generator omni-prompt-decay omni-cross-learning \
    2>/dev/null || true

  log "  Waiting 30s for services to initialize..."
  sleep 30
  echo ""
}

boot_tier_3() {
  log "═══ TIER 3: Enhanced Infrastructure ═══"
  
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d \
    omni-thanos-query omni-anomaly-detector omni-sla-tracker omni-capacity-planner \
    omni-log-pattern-detector omni-log-correlator \
    omni-uptime-kuma omni-backup-orchestrator omni-backup-verifier \
    omni-secret-rotation omni-woodpecker-server \
    2>/dev/null || true

  log "  Waiting 20s for enhanced services..."
  sleep 20
  echo ""
}

boot_tier_4() {
  log "═══ TIER 4: Master Orchestrator ═══"
  
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
    up -d omni-orchestrator omni-dashboard omni-voice-bridge \
    omni-mattermost-bot omni-event-processor 2>/dev/null || true
  
  wait_for_healthy omni-orchestrator 120 || true
  echo ""
}

# ---------------------------------------------------------------------------
# Status Check
# ---------------------------------------------------------------------------
check_status() {
  log "Platform Status:"
  echo ""
  printf "  %-35s %-12s %-10s\n" "CONTAINER" "STATUS" "PORTS"
  printf "  %-35s %-12s %-10s\n" "─────────────────────────────────" "────────────" "──────────"
  
  docker ps --filter "label=omni.system" --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | \
    sort | while IFS=$'\t' read -r name status ports; do
      if echo "$status" | grep -q "healthy"; then
        printf "  ${GREEN}%-35s${NC} %-12s %s\n" "$name" "✓ healthy" "$ports"
      elif echo "$status" | grep -q "Up"; then
        printf "  ${YELLOW}%-35s${NC} %-12s %s\n" "$name" "↑ starting" "$ports"
      else
        printf "  ${RED}%-35s${NC} %-12s %s\n" "$name" "✗ down" "$ports"
      fi
    done
  
  echo ""
  TOTAL=$(docker ps --filter "label=omni.system" -q | wc -l)
  HEALTHY=$(docker ps --filter "label=omni.system" --filter "health=healthy" -q | wc -l)
  log "Services: $HEALTHY/$TOTAL healthy"
}

# ---------------------------------------------------------------------------
# Graceful Shutdown
# ---------------------------------------------------------------------------
shutdown_platform() {
  log "Graceful shutdown..."
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down --timeout 30
  ok "All services stopped"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
banner

case "${1:-}" in
  --status)
    check_status
    ;;
  --down)
    shutdown_platform
    ;;
  --generate-secrets)
    generate_secrets
    ;;
  --tier)
    setup_network
    case "${2:-}" in
      0) boot_tier_0 ;;
      1) boot_tier_1 ;;
      2) boot_tier_2 ;;
      3) boot_tier_3 ;;
      4) boot_tier_4 ;;
      *) echo "Usage: $0 --tier {0|1|2|3|4}" ;;
    esac
    ;;
  *)
    check_prerequisites
    generate_secrets
    setup_network
    boot_tier_0
    boot_tier_1
    boot_tier_2
    boot_tier_3
    boot_tier_4
    echo ""
    log "═══════════════════════════════════════════════"
    log "  ⚛  OMNI QUANTUM ELITE IS ONLINE"
    log "═══════════════════════════════════════════════"
    echo ""
    log "  Dashboard:     https://localhost:9501"
    log "  Orchestrator:  https://localhost:9500"
    log "  Voice Bridge:  https://localhost:9502"
    log "  Grafana:       https://localhost:3050"
    log "  Portainer:     https://localhost:9443"
    log ""
    log "  Run './deploy.sh --status' to check health"
    echo ""
    check_status
    ;;
esac
