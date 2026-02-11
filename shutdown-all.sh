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

down_group() {
  local group_name="$1"
  shift
  local files=("$@")

  log "${BLUE}=== ${group_name} ===${NC}"
  local f
  for f in "${files[@]}"; do
    [[ -f "$f" ]] || continue
    run docker compose -f "$f" down
  done
}

main() {
  command -v docker >/dev/null 2>&1 || { log "${RED}docker not found${NC}"; exit 1; }
  docker compose version >/dev/null 2>&1 || { log "${RED}docker compose plugin not found${NC}"; exit 1; }

  # Reverse order of deploy-all groups
  down_group "Group 16 - Master Orchestrator" \
    omni-quantum-systems/system-37-master-orchestrator/docker-compose.yml \
    services/master-orchestrator/docker-compose.yml

  down_group "Group 15 - Omi Bridge" \
    services/omi-bridge/docker-compose.yml

  down_group "Group 14 - Enhanced Infrastructure" \
    omni-quantum-systems/system-29-enhanced-monitoring/docker-compose.yml \
    omni-quantum-systems/system-30-enhanced-logging/docker-compose.yml \
    omni-quantum-systems/system-31-uptime-monitor/docker-compose.yml \
    omni-quantum-systems/system-32-enhanced-backup/docker-compose.yml \
    omni-quantum-systems/system-33-enhanced-secrets/docker-compose.yml \
    omni-quantum-systems/system-34-enhanced-proxy/docker-compose.yml \
    omni-quantum-systems/system-35-cicd-pipelines/docker-compose.yml \
    omni-quantum-systems/system-36-dev-environments/docker-compose.yml

  down_group "Group 13 - Financial" \
    financial/docker-compose.yml \
    docker-compose.yml

  down_group "Group 12 - Platform Ops" \
    services/feedback-forms/docker-compose.yml \
    services/npm-registry/docker-compose.yml \
    services/db-admin/docker-compose.yml \
    services/container-manager/docker-compose.yml

  down_group "Group 11 - Integration & Validation" \
    services/api-gateway/docker-compose.yml \
    services/contract-testing/docker-compose.yml \
    services/chaos-testing/docker-compose.yml \
    services/ml-tracking/docker-compose.yml \
    services/benchmarking/docker-compose.yml \
    services/distributed-tracing-jaeger/docker-compose.yml \
    services/continuous-profiling-pyroscope/docker-compose.yml \
    services/dast-penetration-testing/docker-compose.yml \
    services/data-validation-framework/docker-compose.yml \
    services/architecture-diagram-generation/docker-compose.yml \
    services/visual-verification-agent/docker-compose.yml

  down_group "Group 10 - Product Suite B" \
    services/email-service/docker-compose.yml \
    services/support-center/docker-compose.yml \
    services/web-analytics/docker-compose.yml \
    services/feature-flags/docker-compose.yml \
    services/error-tracking/docker-compose.yml \
    services/search-engine/docker-compose.yml \
    services/audit-logger/docker-compose.yml \
    services/translation-mgmt/docker-compose.yml \
    services/agentic-sre-self-healing/docker-compose.yml

  down_group "Group 9 - Product Suite A" \
    services/deploy-engine/docker-compose.yml \
    services/flow-builder/docker-compose.yml \
    services/analytics-engine/docker-compose.yml \
    services/schedule-manager/docker-compose.yml

  down_group "Group 8 - Quality & Dev Tooling" \
    services/code-scorer/docker-compose.yml \
    services/gate-engine/docker-compose.yml \
    services/context-compiler/docker-compose.yml \
    services/sourcegraph/docker-compose.yml \
    services/build-forge/docker-compose.yml \
    services/code-forge/docker-compose.yml \
    services/mutation-testing-engine/docker-compose.yml \
    services/database-design-intelligence/docker-compose.yml \
    services/dead-code-detection/docker-compose.yml

  down_group "Group 7 - Knowledge Layer" \
    services/knowledge-ingestor/docker-compose.yml \
    services/knowledge-freshness/docker-compose.yml \
    services/semantic-cache/docker-compose.yml \
    services/domain-specific-intelligence/docker-compose.yml \
    services/hallucinated-dependency-protection/docker-compose.yml

  down_group "Group 6 - AI Runtime & Agents" \
    services/neural-network/docker-compose.yml \
    services/ai-gateway/docker-compose.yml \
    services/token-infinity/docker-compose.yml \
    services/ai-coder-alpha/docker-compose.yml \
    services/ai-coder-beta/docker-compose.yml \
    services/ai-observability/docker-compose.yml \
    services/code-completion-tabby/docker-compose.yml

  down_group "Group 5 - Comms & Automation" \
    services/communication-hub/docker-compose.yml \
    services/flow-architect/docker-compose.yml \
    services/integration-hub/docker-compose.yml

  down_group "Group 4 - Edge/Security" \
    services/gateway-sentinel/docker-compose.yml \
    services/security-nexus/docker-compose.yml \
    services/security-shield/docker-compose.yml

  down_group "Group 3 - Core Platform Dependencies" \
    services/code-fortress/docker-compose.yml \
    services/observatory/docker-compose.yml \
    services/log-nexus/docker-compose.yml \
    services/vector-memory/docker-compose.yml \
    services/neo4j-graphrag/docker-compose.yml

  down_group "Group 2 - Vault / Crypto" \
    services/cryptographic-fortress/docker-compose.yml

  down_group "Group 1 - Foundation Data Plane" \
    services/postgresql/docker-compose.yml \
    services/redis/docker-compose.yml \
    services/object-store/docker-compose.yml

  log "${GREEN}Shutdown complete${NC}"
}

main "$@"
