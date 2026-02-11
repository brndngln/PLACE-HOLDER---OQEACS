#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

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

  add_to_tier 0 services/postgresql/docker-compose.yml
  add_to_tier 0 services/redis/docker-compose.yml
  add_to_tier 0 services/object-store/docker-compose.yml

  add_to_tier 1 services/cryptographic-fortress/docker-compose.yml
  add_to_tier 1 services/security-nexus/docker-compose.yml
  add_to_tier 1 services/observatory/docker-compose.yml
  add_to_tier 1 services/log-nexus/docker-compose.yml
  add_to_tier 1 services/gateway-sentinel/docker-compose.yml

  add_to_tier 2 services/neural-network/docker-compose.yml
  add_to_tier 2 services/ai-gateway/docker-compose.yml
  add_to_tier 2 services/vector-memory/docker-compose.yml
  add_to_tier 2 services/code-fortress/docker-compose.yml

  add_to_tier 4 omni-quantum-systems/system-29-enhanced-monitoring/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-30-enhanced-logging/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-31-uptime-monitor/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-32-enhanced-backup/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-33-enhanced-secrets/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-34-enhanced-proxy/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-35-cicd-pipelines/docker-compose.yml
  add_to_tier 4 omni-quantum-systems/system-36-dev-environments/docker-compose.yml

  add_to_tier 5 omni-quantum-systems/system-37-master-orchestrator/docker-compose.yml

  local f
  for f in "${ALL_COMPOSES[@]}"; do
    if [[ -z "${ASSIGNED[$f]:-}" ]]; then
      TIER3+=("$f")
    fi
  done
}

down_tier() {
  local tier_name="$1"
  shift
  local files=("$@")

  log "${BLUE}=== ${tier_name} ===${NC}"
  local f
  for f in "${files[@]}"; do
    if [[ -f "$f" ]]; then
      run docker compose -f "$f" down
    fi
  done
}

main() {
  command -v docker >/dev/null 2>&1 || { log "${RED}docker not found${NC}"; exit 1; }
  docker compose version >/dev/null 2>&1 || { log "${RED}docker compose plugin not found${NC}"; exit 1; }

  build_tiers

  down_tier "Tier 5 - Master Orchestrator (37)" "${TIER5[@]}"
  down_tier "Tier 4 - Enhanced Infrastructure (29-36)" "${TIER4[@]}"
  down_tier "Tier 3 - Application Services" "${TIER3[@]}"
  down_tier "Tier 2 - Core AI/Code" "${TIER2[@]}"
  down_tier "Tier 1 - Security/Observability/Ingress" "${TIER1[@]}"
  down_tier "Tier 0 - Foundation" "${TIER0[@]}"

  log "${GREEN}Shutdown complete${NC}"
}

main "$@"
