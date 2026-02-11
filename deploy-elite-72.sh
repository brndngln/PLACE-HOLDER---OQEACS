#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.elite-72.yml"
export MLFLOW_DB_PASSWORD="${MLFLOW_DB_PASSWORD:-}"

declare -A WAVE_LABELS=(
  [agent-intelligence]='Wave A'
  [code-generation]='Wave B'
  [qa-verification]='Wave C'
  [knowledge-intelligence]='Wave D'
  [domain-packs]='Wave E'
  [developer-experience]='Wave F'
  [infrastructure-ops]='Wave G'
)

AGENT_INTELLIGENCE_SERVICES=(omni-uncertainty-planner omni-patch-tree omni-agent-memory-bus omni-tool-policy omni-escalation-router omni-spec-clarifier omni-redteam-agent omni-elite-prompt-circuit-breaker)
CODE_GENERATION_SERVICES=(omni-lsp-refactor omni-buildgraph-planner omni-compile-loop omni-contract-synth omni-ffi-wasm-gen omni-lifetime-reasoner omni-query-plan-gen omni-algo-selector)
QA_VERIFICATION_SERVICES=(omni-cpg-analyzer omni-abstract-verify omni-concurrency-static omni-sanitizer-orch omni-api-fuzz-stateful omni-native-fuzz-cluster omni-diff-oracle omni-crypto-harness omni-elite-tier2-fast-verification omni-elite-clean-room-reproducibility omni-elite-test-signal-fusion)
KNOWLEDGE_INTELLIGENCE_SERVICES=(omni-vuln-graph omni-dep-trust omni-migration-diff omni-rag-eval omni-context-compress omni-knowledge-trust omni-repro-miner omni-elite-dependency-existence-validation omni-elite-cross-repo-intel omni-elite-database-intelligence)
DOMAIN_PACKS_SERVICES=(omni-fhir-pack omni-finance-rules-pack omni-identity-pack omni-chain-pack omni-iot-pack omni-extension-pack omni-desktop-pack omni-webrtc-pack omni-elt-pack omni-game-pack)
DEVELOPER_EXPERIENCE_SERVICES=(omni-lineage-explorer omni-semantic-diff omni-rca-synth omni-bug-replay omni-minrepro omni-preview-env omni-handoff-compiler omni-generation-lineage omni-elite-architecture-fitness omni-elite-error-pattern-intel omni-elite-semantic-intent-verification omni-elite-architecture-rule-enforcement omni-elite-adr-tracking omni-elite-design-intelligence)
INFRASTRUCTURE_OPS_SERVICES=(omni-k8s-target omni-progressive-delivery omni-mesh-identity omni-admission-guard omni-ebpf-forensics omni-cost-optimizer omni-slo-framework omni-elite-runtime-drift-detector omni-elite-mcp-orchestrator omni-elite-chaos-guard omni-elite-release-readiness)

notify() {
  local message="$1"
  echo "$message"
  if [[ -n "${MATTERMOST_WEBHOOK_URL:-}" ]]; then
    curl -sS -X POST -H 'Content-Type: application/json' \
      -d "{\"text\":\"$message\"}" \
      "$MATTERMOST_WEBHOOK_URL" >/dev/null || true
  fi
}

require_prereqs() {
  command -v docker >/dev/null 2>&1 || { echo "docker not found"; exit 1; }
  docker compose version >/dev/null 2>&1 || { echo "docker compose not found"; exit 1; }
  docker network inspect omni-quantum-network >/dev/null 2>&1 || {
    echo "Docker network omni-quantum-network not found"
    exit 1
  }
}

wait_for_wave_health() {
  local profile="$1"
  local services=()
  case "$profile" in
    agent-intelligence) services=("${AGENT_INTELLIGENCE_SERVICES[@]}") ;;
    code-generation) services=("${CODE_GENERATION_SERVICES[@]}") ;;
    qa-verification) services=("${QA_VERIFICATION_SERVICES[@]}") ;;
    knowledge-intelligence) services=("${KNOWLEDGE_INTELLIGENCE_SERVICES[@]}") ;;
    domain-packs) services=("${DOMAIN_PACKS_SERVICES[@]}") ;;
    developer-experience) services=("${DEVELOPER_EXPERIENCE_SERVICES[@]}") ;;
    infrastructure-ops) services=("${INFRASTRUCTURE_OPS_SERVICES[@]}") ;;
    *) echo "Unknown profile $profile"; return 1 ;;
  esac

  for service in "${services[@]}"; do
    local retries=60
    local healthy="false"
    while (( retries > 0 )); do
      local status
      status=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$service" 2>/dev/null || true)
      if [[ "$status" == "healthy" ]]; then
        healthy="true"
        break
      fi
      sleep 5
      ((retries--))
    done
    if [[ "$healthy" != "true" ]]; then
      echo "Service failed health check: $service"
      docker logs --tail 100 "$service" || true
      return 1
    fi
  done
}

deploy_wave() {
  local profile="$1"
  notify "Deploying ${WAVE_LABELS[$profile]} ($profile)..."
  docker compose -f "$COMPOSE_FILE" --profile "$profile" up -d --build
  wait_for_wave_health "$profile"
  notify "Wave healthy: ${WAVE_LABELS[$profile]}"
}

main() {
  require_prereqs
  notify "Starting elite wave deployment (estimated 10-15 minutes)."

  [[ "${DEPLOY_WAVE_A:-true}" == "true" ]] && deploy_wave "agent-intelligence"
  [[ "${DEPLOY_WAVE_B:-true}" == "true" ]] && deploy_wave "code-generation"
  [[ "${DEPLOY_WAVE_C:-true}" == "true" ]] && deploy_wave "qa-verification"
  [[ "${DEPLOY_WAVE_D:-true}" == "true" ]] && deploy_wave "knowledge-intelligence"
  [[ "${DEPLOY_WAVE_E:-true}" == "true" ]] && deploy_wave "domain-packs"
  [[ "${DEPLOY_WAVE_F:-true}" == "true" ]] && deploy_wave "developer-experience"
  [[ "${DEPLOY_WAVE_G:-true}" == "true" ]] && deploy_wave "infrastructure-ops"

  notify "Elite deployment complete."
}

main "$@"
