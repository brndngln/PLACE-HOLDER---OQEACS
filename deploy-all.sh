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
    log "${YELLOW}No containers for $compose_file (skip health gate)${NC}"
    return 0
  fi

  while [[ "$elapsed" -lt "$MAX_HEALTH_WAIT" ]]; do
    local all_ready=1
    local cid state

    for cid in $containers; do
      state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || echo missing)"
      case "$state" in
        healthy|running) ;;
        starting|created|restarting) all_ready=0 ;;
        exited|dead|unhealthy|missing)
          log "${RED}Container $cid from $compose_file is $state${NC}"
          return 1
          ;;
        *) all_ready=0 ;;
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

up_group() {
  local group_name="$1"
  shift
  local files=("$@")

  log "${BLUE}=== ${group_name} ===${NC}"

  local f
  for f in "${files[@]}"; do
    [[ -f "$f" ]] || continue
    run docker compose -f "$f" up -d
  done

  if [[ "$DRY_RUN" != "1" ]]; then
    for f in "${files[@]}"; do
      [[ -f "$f" ]] || continue
      wait_compose_healthy "$f"
    done
  fi
}

main() {
  require_tools

  if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    run docker network create "$NETWORK_NAME"
  fi

  # Group 1: PostgreSQL, Redis, MinIO (foundation)
  up_group "Group 1 - Foundation Data Plane" \
    services/postgresql/docker-compose.yml \
    services/redis/docker-compose.yml \
    services/object-store/docker-compose.yml

  # Group 2: Vault
  up_group "Group 2 - Vault / Crypto" \
    services/cryptographic-fortress/docker-compose.yml

  # Group 3: Gitea, Prometheus+Grafana, Loki+Promtail, Qdrant, Neo4j
  up_group "Group 3 - Core Platform Dependencies" \
    services/code-fortress/docker-compose.yml \
    services/observatory/docker-compose.yml \
    services/log-nexus/docker-compose.yml \
    services/vector-memory/docker-compose.yml \
    services/neo4j-graphrag/docker-compose.yml

  # Group 4: Traefik, Authentik, CrowdSec, Secret Rotation
  up_group "Group 4 - Edge/Security" \
    services/gateway-sentinel/docker-compose.yml \
    services/security-nexus/docker-compose.yml \
    services/security-shield/docker-compose.yml

  # Group 5: Mattermost, n8n, Nango
  up_group "Group 5 - Comms & Automation" \
    services/communication-hub/docker-compose.yml \
    services/flow-architect/docker-compose.yml \
    services/integration-hub/docker-compose.yml

  # Group 6: Ollama, LiteLLM, Token Infinity, OpenHands, SWE-Agent, Langfuse
  up_group "Group 6 - AI Runtime & Agents" \
    services/neural-network/docker-compose.yml \
    services/ai-gateway/docker-compose.yml \
    services/token-infinity/docker-compose.yml \
    services/ai-coder-alpha/docker-compose.yml \
    services/ai-coder-beta/docker-compose.yml \
    services/ai-observability/docker-compose.yml

  # Group 7: Knowledge services
  up_group "Group 7 - Knowledge Layer" \
    services/knowledge-ingestor/docker-compose.yml \
    services/knowledge-freshness/docker-compose.yml \
    services/semantic-cache/docker-compose.yml

  # Group 8: Code quality + dev infra
  up_group "Group 8 - Quality & Dev Tooling" \
    services/code-scorer/docker-compose.yml \
    services/gate-engine/docker-compose.yml \
    services/context-compiler/docker-compose.yml \
    services/sourcegraph/docker-compose.yml \
    services/build-forge/docker-compose.yml \
    services/code-forge/docker-compose.yml

  # Group 9: Coolify, Flowise, Superset, Cal.com
  up_group "Group 9 - Product Suite A" \
    services/deploy-engine/docker-compose.yml \
    services/flow-builder/docker-compose.yml \
    services/analytics-engine/docker-compose.yml \
    services/schedule-manager/docker-compose.yml

  # Group 10: Business infra
  up_group "Group 10 - Product Suite B" \
    services/email-service/docker-compose.yml \
    services/support-center/docker-compose.yml \
    services/web-analytics/docker-compose.yml \
    services/feature-flags/docker-compose.yml \
    services/error-tracking/docker-compose.yml \
    services/search-engine/docker-compose.yml \
    services/audit-logger/docker-compose.yml \
    services/translation-mgmt/docker-compose.yml

  # Group 11: Gateway/testing/ml/bench
  up_group "Group 11 - Integration & Validation" \
    services/api-gateway/docker-compose.yml \
    services/contract-testing/docker-compose.yml \
    services/chaos-testing/docker-compose.yml \
    services/ml-tracking/docker-compose.yml \
    services/benchmarking/docker-compose.yml

  # Group 12: Forms, package/admin, container mgmt
  up_group "Group 12 - Platform Ops" \
    services/feedback-forms/docker-compose.yml \
    services/npm-registry/docker-compose.yml \
    services/db-admin/docker-compose.yml \
    services/container-manager/docker-compose.yml

  # Group 13: Financial services
  up_group "Group 13 - Financial" \
    docker-compose.yml \
    financial/docker-compose.yml

  # Group 14: Enhanced infrastructure (29-36)
  up_group "Group 14 - Enhanced Infrastructure" \
    omni-quantum-systems/system-29-enhanced-monitoring/docker-compose.yml \
    omni-quantum-systems/system-30-enhanced-logging/docker-compose.yml \
    omni-quantum-systems/system-31-uptime-monitor/docker-compose.yml \
    omni-quantum-systems/system-32-enhanced-backup/docker-compose.yml \
    omni-quantum-systems/system-33-enhanced-secrets/docker-compose.yml \
    omni-quantum-systems/system-34-enhanced-proxy/docker-compose.yml \
    omni-quantum-systems/system-35-cicd-pipelines/docker-compose.yml \
    omni-quantum-systems/system-36-dev-environments/docker-compose.yml

  # Group 15: Omi wearable bridge
  up_group "Group 15 - Omi Bridge" \
    services/omi-bridge/docker-compose.yml

  # Group 16: Master orchestrator (last)
  up_group "Group 16 - Master Orchestrator" \
    omni-quantum-systems/system-37-master-orchestrator/docker-compose.yml \
    services/master-orchestrator/docker-compose.yml

  log "${GREEN}Deployment complete${NC}"
}

main "$@"
