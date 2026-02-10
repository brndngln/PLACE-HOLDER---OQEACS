#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-./logs}"
LOG_FILE="${LOG_DIR}/shutdown-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$LOG_DIR"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"; }
compose_down() { [ -f "$1" ] && docker compose -f "$1" down || log "skip missing $1"; }

log "Stopping master orchestrator first"
compose_down services/master-orchestrator/docker-compose.yml

for file in \
  services/omi-bridge/docker-compose.yml \
  services/enhanced-backup/docker-compose.yml services/uptime-monitor/docker-compose.yml services/enhanced-logging/docker-compose.yml services/enhanced-monitoring/docker-compose.yml \
  services/financial/docker-compose.yml \
  services/container-manager/docker-compose.yml services/db-admin/docker-compose.yml services/npm-registry/docker-compose.yml services/feedback-forms/docker-compose.yml \
  services/benchmarking/docker-compose.yml services/ml-tracking/docker-compose.yml services/chaos-testing/docker-compose.yml services/contract-testing/docker-compose.yml services/api-gateway/docker-compose.yml \
  services/translation-mgmt/docker-compose.yml services/audit-logger/docker-compose.yml services/search-engine/docker-compose.yml services/error-tracking/docker-compose.yml services/feature-flags/docker-compose.yml services/web-analytics/docker-compose.yml services/support-center/docker-compose.yml services/email-service/docker-compose.yml \
  services/invoice-manager/docker-compose.yml services/crm-hub/docker-compose.yml services/schedule-manager/docker-compose.yml services/analytics-engine/docker-compose.yml services/flow-builder/docker-compose.yml services/deploy-engine/docker-compose.yml services/project-command/docker-compose.yml \
  services/code-forge/docker-compose.yml services/build-forge/docker-compose.yml services/sourcegraph/docker-compose.yml services/context-compiler/docker-compose.yml services/gate-engine/docker-compose.yml services/code-scorer/docker-compose.yml \
  services/knowledge-base/docker-compose.yml services/semantic-cache/docker-compose.yml services/knowledge-freshness/docker-compose.yml services/knowledge-ingestor/docker-compose.yml \
  services/ai-observability/docker-compose.yml services/ai-coder-beta/docker-compose.yml services/ai-coder-alpha/docker-compose.yml services/token-infinity/docker-compose.yml services/ai-gateway/docker-compose.yml services/neural-network/docker-compose.yml \
  services/integration-hub/docker-compose.yml services/workflow-engine/docker-compose.yml services/communication-hub/docker-compose.yml \
  services/cryptographic-fortress-pro/docker-compose.yml services/security-shield/docker-compose.yml services/security-nexus/docker-compose.yml services/gateway-sentinel/docker-compose.yml \
  services/neo4j-graphrag/docker-compose.yml services/vector-memory/docker-compose.yml services/log-nexus/docker-compose.yml services/observatory/docker-compose.yml services/code-fortress/docker-compose.yml \
  services/cryptographic-fortress/docker-compose.yml services/object-store/docker-compose.yml services/infrastructure/redis/docker-compose.yml services/infrastructure/postgres/docker-compose.yml
 do
  compose_down "$file"
 done

TOTAL=$(docker ps --filter "label=omni.quantum.component" --format '{{.Names}}' | wc -l | tr -d ' ')
log "Shutdown complete. Running omni containers: $TOTAL"
log "Data volumes preserved."
