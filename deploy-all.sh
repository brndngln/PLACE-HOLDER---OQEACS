#!/usr/bin/env bash
set -Eeuo pipefail

COMPOSE_PROJECT_NAME="omni-quantum"
NETWORK_NAME="omni-quantum-network"
MAX_HEALTH_WAIT="${MAX_HEALTH_WAIT:-180}"
LOG_DIR="${LOG_DIR:-./logs}"
LOG_FILE="${LOG_DIR}/deploy-$(date +%Y%m%d-%H%M%S).log"
DRY_RUN="${DRY_RUN:-0}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

mkdir -p "$LOG_DIR"

log() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"; }
log_header() { log "${BLUE}═══════════════════════════════════════${NC}"; log "${BLUE} $1${NC}"; log "${BLUE}═══════════════════════════════════════${NC}"; }

cleanup() { log "${RED}Deployment failed. Check: ${LOG_FILE}${NC}"; }
trap cleanup ERR

run_cmd() {
  if [[ "$DRY_RUN" == "1" ]]; then
    log "${YELLOW}[dry-run] $*${NC}"
  else
    "$@"
  fi
}

wait_healthy() {
  local service="$1" url="$2" timeout="${3:-$MAX_HEALTH_WAIT}" elapsed=0
  log "${YELLOW}⏳ Waiting for $service...${NC}"
  while [ "$elapsed" -lt "$timeout" ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "${GREEN}✅ $service healthy (${elapsed}s)${NC}"
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  log "${RED}❌ $service failed health check: $url${NC}"
  return 1
}

compose_up() {
  local file="$1"
  if [ -f "$file" ]; then
    run_cmd docker compose -f "$file" up -d
  else
    log "${YELLOW}⚠️ Missing compose file: $file (skipping)${NC}"
  fi
}

run_init() {
  local script="$1"
  if [ -f "$script" ]; then
    run_cmd bash "$script"
  else
    log "${YELLOW}⚠️ Missing init script: $script (skipping)${NC}"
  fi
}

compose_group() {
  local title="$1"; shift
  log_header "$title"
  local item
  for item in "$@"; do
    compose_up "$item"
  done
}

check_deps() {
  command -v docker >/dev/null || { log "${RED}Docker not found${NC}"; exit 1; }
  docker compose version >/dev/null || { log "${RED}Docker Compose plugin not found${NC}"; exit 1; }
  command -v curl >/dev/null || { log "${RED}curl not found${NC}"; exit 1; }
}

log_header "PRE-FLIGHT CHECKS"
check_deps
[ -f .env ] && source .env || log "${YELLOW}⚠️ .env not found; using environment defaults${NC}"

docker network inspect "$NETWORK_NAME" >/dev/null 2>&1 || {
  run_cmd docker network create "$NETWORK_NAME"
  log "${GREEN}Created network $NETWORK_NAME${NC}"
}

compose_group "GROUP 1: DATABASES & STORAGE" \
  services/infrastructure/postgres/docker-compose.yml \
  services/infrastructure/redis/docker-compose.yml \
  services/object-store/docker-compose.yml
wait_healthy "MinIO" "http://localhost:9000/minio/health/live" 180 || true

compose_group "GROUP 2: SECURITY FOUNDATION" \
  services/cryptographic-fortress/docker-compose.yml
wait_healthy "Vault" "http://localhost:8200/v1/sys/health" 180 || true
run_init services/cryptographic-fortress/scripts/vault-init.sh
run_init services/cryptographic-fortress/seed-secrets.sh

compose_group "GROUP 3: CORE SERVICES" \
  services/code-fortress/docker-compose.yml \
  services/observatory/docker-compose.yml \
  services/log-nexus/docker-compose.yml \
  services/vector-memory/docker-compose.yml \
  services/neo4j-graphrag/docker-compose.yml
wait_healthy "Gitea" "http://localhost:3000/api/v1/version" 180 || true
wait_healthy "Prometheus" "http://localhost:9090/-/healthy" 180 || true
wait_healthy "Loki" "http://localhost:3100/ready" 180 || true
wait_healthy "Qdrant" "http://localhost:6333/healthz" 180 || true
run_init services/code-fortress/scripts/gitea-init.sh
[ -f services/vector-memory/scripts/qdrant-init.py ] && run_cmd python services/vector-memory/scripts/qdrant-init.py || true
[ -f services/neo4j-graphrag/seed/run-init.py ] && run_cmd python services/neo4j-graphrag/seed/run-init.py || true

compose_group "GROUP 4: SECURITY LAYER" \
  services/gateway-sentinel/docker-compose.yml \
  services/security-nexus/docker-compose.yml \
  services/security-shield/docker-compose.yml \
  services/cryptographic-fortress-pro/docker-compose.yml
wait_healthy "Traefik" "http://localhost:8080/ping" 180 || true
wait_healthy "Authentik" "http://localhost:9000/-/health/live/" 180 || true
run_init services/security-shield/scripts/crowdsec-init.sh

compose_group "GROUP 5: COMMUNICATION" \
  services/communication-hub/docker-compose.yml \
  services/workflow-engine/docker-compose.yml \
  services/integration-hub/docker-compose.yml
wait_healthy "Mattermost" "http://localhost:8065/api/v4/system/ping" 180 || true
wait_healthy "n8n" "http://localhost:5678/healthz" 180 || true
run_init services/communication-hub/scripts/mattermost-init.sh
run_init services/workflow-engine/scripts/n8n-import.sh

compose_group "GROUP 6: AI PIPELINE" \
  services/neural-network/docker-compose.yml \
  services/ai-gateway/docker-compose.yml \
  services/token-infinity/docker-compose.yml \
  services/ai-coder-alpha/docker-compose.yml \
  services/ai-coder-beta/docker-compose.yml \
  services/ai-observability/docker-compose.yml
wait_healthy "LiteLLM" "http://localhost:4000/health" 180 || true
wait_healthy "Token Infinity Context" "http://localhost:9600/health" 180 || true
run_init services/neural-network/scripts/model-init.sh

compose_group "GROUP 7: KNOWLEDGE LAYER" \
  services/knowledge-ingestor/docker-compose.yml \
  services/knowledge-freshness/docker-compose.yml \
  services/semantic-cache/docker-compose.yml \
  services/knowledge-base/docker-compose.yml
wait_healthy "Knowledge Ingestor" "http://localhost:9420/health" 180 || true
wait_healthy "Freshness" "http://localhost:9430/health" 180 || true
wait_healthy "Semantic Cache" "http://localhost:9440/health" 180 || true
run_init services/knowledge-base/scripts/wiki-init.sh
run_init services/knowledge-base/scripts/seed-wiki.sh

compose_group "GROUP 8: PIPELINE SERVICES" \
  services/code-scorer/docker-compose.yml \
  services/gate-engine/docker-compose.yml \
  services/context-compiler/docker-compose.yml \
  services/sourcegraph/docker-compose.yml \
  services/build-forge/docker-compose.yml \
  services/code-forge/docker-compose.yml
run_init services/build-forge/scripts/woodpecker-init.sh
run_init services/code-forge/scripts/coder-init.sh

compose_group "GROUP 9: BUSINESS OPERATIONS" \
  services/project-command/docker-compose.yml \
  services/deploy-engine/docker-compose.yml \
  services/flow-builder/docker-compose.yml \
  services/analytics-engine/docker-compose.yml \
  services/schedule-manager/docker-compose.yml \
  services/crm-hub/docker-compose.yml \
  services/invoice-manager/docker-compose.yml
run_init services/project-command/scripts/plane-init.sh
run_init services/deploy-engine/scripts/coolify-init.sh
run_init services/schedule-manager/scripts/calcom-init.sh

compose_group "GROUP 10: BUSINESS INFRASTRUCTURE" \
  services/email-service/docker-compose.yml \
  services/support-center/docker-compose.yml \
  services/web-analytics/docker-compose.yml \
  services/feature-flags/docker-compose.yml \
  services/error-tracking/docker-compose.yml \
  services/search-engine/docker-compose.yml \
  services/audit-logger/docker-compose.yml \
  services/translation-mgmt/docker-compose.yml
run_init services/email-service/scripts/listmonk-init.sh
run_init services/search-engine/scripts/meilisearch-init.sh

compose_group "GROUP 11: TESTING & QUALITY" \
  services/api-gateway/docker-compose.yml \
  services/contract-testing/docker-compose.yml \
  services/chaos-testing/docker-compose.yml \
  services/ml-tracking/docker-compose.yml \
  services/benchmarking/docker-compose.yml
wait_healthy "Kong" "http://localhost:8100/status" 180 || true
wait_healthy "Pact Broker" "http://localhost:9292/diagnostic/status/heartbeat" 180 || true
wait_healthy "Toxiproxy" "http://localhost:8474/version" 180 || true
wait_healthy "MLflow" "http://localhost:5000/health" 180 || true
run_init services/api-gateway/scripts/kong-init.sh
run_init services/contract-testing/scripts/pact-init.sh
run_init services/chaos-testing/scripts/toxiproxy-init.sh
run_init services/ml-tracking/scripts/mlflow-init.sh
run_init services/benchmarking/scripts/bencher-init.sh

compose_group "GROUP 12: DX & REMAINING" \
  services/feedback-forms/docker-compose.yml \
  services/npm-registry/docker-compose.yml \
  services/db-admin/docker-compose.yml \
  services/container-manager/docker-compose.yml
wait_healthy "Formbricks" "http://localhost:3010/api/health" 180 || true
wait_healthy "Verdaccio" "http://localhost:4873/-/ping" 180 || true
wait_healthy "CloudBeaver" "http://localhost:8978/status" 180 || true
run_init services/feedback-forms/scripts/formbricks-init.sh
run_init services/npm-registry/scripts/verdaccio-init.sh
run_init services/db-admin/scripts/cloudbeaver-init.sh
run_init services/container-manager/scripts/portainer-init.sh

compose_group "GROUP 13: FINANCIAL MICROSERVICES" services/financial/docker-compose.yml
compose_group "GROUP 14: ENHANCED MONITORING" \
  services/enhanced-monitoring/docker-compose.yml \
  services/enhanced-logging/docker-compose.yml \
  services/uptime-monitor/docker-compose.yml \
  services/enhanced-backup/docker-compose.yml

compose_group "GROUP 15: OMI WEARABLE" services/omi-bridge/docker-compose.yml
wait_healthy "Omi Bridge" "http://localhost:9700/health" 120 || true

compose_group "GROUP 16: MASTER ORCHESTRATOR" services/master-orchestrator/docker-compose.yml
wait_healthy "Master Orchestrator" "http://localhost:9500/health" 180 || true
curl -fsS -X POST http://localhost:9500/api/services/discover >/dev/null 2>&1 || true
[ -f services/master-orchestrator/config/service-registry-update.py ] && run_cmd python services/master-orchestrator/config/service-registry-update.py || true

log_header "FINAL VERIFICATION"
TOTAL=$(docker ps --filter "label=omni.quantum.component" --format '{{.Names}}' | wc -l | tr -d ' ')
HEALTHY=$(docker ps --filter "label=omni.quantum.component" --filter "health=healthy" --format '{{.Names}}' | wc -l | tr -d ' ')
UNHEALTHY=$(docker ps --filter "label=omni.quantum.component" --filter "health=unhealthy" --format '{{.Names}}' | wc -l | tr -d ' ')

log "${GREEN}OMNI QUANTUM ELITE DEPLOYMENT COMPLETE${NC}"
log "Total containers: $TOTAL"
log "Healthy: $HEALTHY"
log "Unhealthy: $UNHEALTHY"
log "Log file: $LOG_FILE"

if [[ -n "${MATTERMOST_WEBHOOK_URL:-}" ]]; then
  curl -fsS -X POST "$MATTERMOST_WEBHOOK_URL" -H "Content-Type: application/json" \
    -d "{\"channel\":\"general\",\"username\":\"omnibot\",\"icon_emoji\":\":rocket:\",\"text\":\"## ⚛️ Omni Quantum Elite Platform Deployed\\n**Containers:** $TOTAL running ($HEALTHY healthy)\\n**Time:** $(date)\\n**Log:** $LOG_FILE\"}" || true
fi
