#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

NETWORK_NAME="omni-quantum-network"
MAX_HEALTH_WAIT="${MAX_HEALTH_WAIT:-300}"
SLEEP_INTERVAL="${SLEEP_INTERVAL:-3}"
DRY_RUN="${DRY_RUN:-0}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') $*"; }
run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    log "${YELLOW}[dry-run] $*${NC}"
  else
    "$@"
  fi
}

require_tools() {
  command -v docker >/dev/null 2>&1 || { log "${RED}docker not found${NC}"; exit 1; }
  docker compose version >/dev/null 2>&1 || { log "${RED}docker compose plugin not found${NC}"; exit 1; }
}

wait_compose_healthy() {
  local compose_file="$1"
  local elapsed=0
  local containers=""

  containers="$(docker compose -f "$compose_file" ps -q 2>/dev/null || true)"
  if [[ -z "$containers" ]]; then
    log "${YELLOW}No containers for $compose_file (skipping health gate)${NC}"
    return 0
  fi

  while [[ "$elapsed" -lt "$MAX_HEALTH_WAIT" ]]; do
    local all_ready=1
    local cid state

    for cid in $containers; do
      state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || echo missing)"
      case "$state" in
        healthy|running)
          ;;
        starting|created|restarting)
          all_ready=0
          ;;
        exited|dead|unhealthy|missing)
          log "${RED}Container $cid from $compose_file is $state${NC}"
          return 1
          ;;
        *)
          all_ready=0
          ;;
      esac
    done

    if [[ "$all_ready" -eq 1 ]]; then
      log "${GREEN}Healthy: $compose_file${NC}"
      return 0
    fi

    sleep "$SLEEP_INTERVAL"
    elapsed=$((elapsed + SLEEP_INTERVAL))
  done

  log "${RED}Timed out waiting for health: $compose_file${NC}"
  return 1
}

up_tier() {
  local tier_name="$1"
  shift
  local files=("$@")

  log "${BLUE}=== ${tier_name} ===${NC}"
  for f in "${files[@]}"; do
    if [[ -f "$f" ]]; then
      run docker compose -f "$f" up -d
    fi
  done

  if [[ "$DRY_RUN" != "1" ]]; then
    for f in "${files[@]}"; do
      if [[ -f "$f" ]]; then
        wait_compose_healthy "$f"
      fi
    done
  fi
}

declare -A ASSIGNED
TIER0=()
TIER1=()
TIER2=()
TIER3=()
TIER4=()
TIER5=()

add_to_tier() {
  local tier="$1"
  local file="$2"
  [[ -f "$file" ]] || return 0
  ASSIGNED["$file"]=1
  case "$tier" in
    0) TIER0+=("$file") ;;
    1) TIER1+=("$file") ;;
    2) TIER2+=("$file") ;;
    4) TIER4+=("$file") ;;
    5) TIER5+=("$file") ;;
  esac
}

build_tiers() {
  mapfile -t ALL_COMPOSES < <(find services omni-quantum-systems -name docker-compose.yml | sort)

  # Tier 0: foundation data plane
  add_to_tier 0 services/postgresql/docker-compose.yml
  add_to_tier 0 services/redis/docker-compose.yml
  add_to_tier 0 services/object-store/docker-compose.yml

  # Tier 1: security + observability + ingress
  add_to_tier 1 services/cryptographic-fortress/docker-compose.yml
  add_to_tier 1 services/security-nexus/docker-compose.yml
  add_to_tier 1 services/observatory/docker-compose.yml
  add_to_tier 1 services/log-nexus/docker-compose.yml
  add_to_tier 1 services/gateway-sentinel/docker-compose.yml

  # Tier 2: core AI/dev dependencies
  add_to_tier 2 services/neural-network/docker-compose.yml
  add_to_tier 2 services/ai-gateway/docker-compose.yml
  add_to_tier 2 services/vector-memory/docker-compose.yml
  add_to_tier 2 services/code-fortress/docker-compose.yml

  # Tier 4: enhanced infrastructure systems 29-36
  add_to_tier 4 omni-quantum-systems/system-29-enhanced-monitoring/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-30-enhanced-logging/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-31-uptime-monitor/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-32-enhanced-backup/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-33-enhanced-secrets/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-34-enhanced-proxy/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-35-cicd-pipelines/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-36-dev-environments/docker-compose.yml

  # Tier 5: master orchestrator
  add_to_tier 5 omni-quantum-systems/system-37-master-orchestrator/docker-compose.yml

  # Tier 3: all other application services
  local f
  for f in "${ALL_COMPOSES[@]}"; do
    if [[ -z "${ASSIGNED[$f]:-}" ]]; then
      TIER3+=("$f")
    fi
  done
}

main() {
  require_tools

  if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    run docker network create "$NETWORK_NAME"
  fi

  build_tiers

  up_tier "Tier 0 - Foundation" "${TIER0[@]}"
  up_tier "Tier 1 - Security/Observability/Ingress" "${TIER1[@]}"
  up_tier "Tier 2 - Core AI/Code" "${TIER2[@]}"
  up_tier "Tier 3 - Application Services" "${TIER3[@]}"
  up_tier "Tier 4 - Enhanced Infrastructure (29-36)" "${TIER4[@]}"
  up_tier "Tier 5 - Master Orchestrator (37)" "${TIER5[@]}"

  log "${GREEN}Deployment complete${NC}"
}

main "$@"
