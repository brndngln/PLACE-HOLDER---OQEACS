#!/usr/bin/env bash

alias omni-status='curl -sf http://omni-orchestrator:9500/api/v1/overview | jq'
alias omni-health='curl -sf http://omni-orchestrator:9500/api/v1/status | jq ".[] | {name: .codename, status: .status, health: .health_status}"'
alias omni-services='curl -sf http://omni-orchestrator:9500/api/v1/status | jq -r ".[] | \"\(.status_icon // \"•\") \(.codename)\t\(.health_status)\t\(.tier)\""'
alias omni-critical='curl -sf http://omni-orchestrator:9500/api/v1/status | jq "[.[] | select(.tier == \"critical\")] | .[] | {name: .codename, health: .health_status}"'

omni-build() { curl -sf -X POST http://omni-orchestrator:9500/api/v1/action/build -H "Content-Type: application/json" -d "{\"description\": \"$1\", \"task_type\": \"${2:-feature-build}\", \"complexity\": \"${3:-medium}\", \"language\": \"${4:-python}\"}"; }
alias omni-tasks='curl -sf http://omni-openhands-orchestrator:3001/tasks | jq ".[] | {id: .task_id, status: .status, type: .task_type, score: .quality_score}"'
alias omni-scores='curl -sf http://omni-orchestrator:9500/api/v1/pipeline/scores 2>/dev/null || echo "Pipeline scores endpoint not available"'
omni-approve() { curl -sf -X POST "http://omni-openhands-orchestrator:3001/tasks/$1/approve" | jq; }
omni-reject() { curl -sf -X POST "http://omni-openhands-orchestrator:3001/tasks/$1/reject" -H "Content-Type: application/json" -d "{\"feedback\": \"$2\"}" | jq; }

alias omni-models='curl -sf http://omni-model-manager:11435/models | jq ".[] | {name: .name, loaded: .loaded, vram_gb: .vram_allocated_gb, tokens_per_sec: .avg_tokens_per_sec}"'
alias omni-gpu='curl -sf http://omni-model-manager:11435/gpu/status | jq "{total_gb: (.vram_total_bytes/1073741824 | floor), used_gb: (.vram_used_bytes/1073741824 | floor), free_gb: (.vram_free_bytes/1073741824 | floor), utilization: .gpu_utilization_percent, temp_c: .gpu_temperature_celsius}"'
omni-load-model() { curl -sf -X POST http://omni-model-manager:11435/models/load -H "Content-Type: application/json" -d "{\"name\": \"$1\"}" | jq; }
omni-unload-model() { curl -sf -X POST "http://omni-model-manager:11435/models/unload/$1" | jq; }
omni-benchmark-model() { curl -sf -X POST "http://omni-model-manager:11435/models/benchmark/$1" | jq; }

alias omni-knowledge='curl -sf http://omni-knowledge-ingestor:9420/ingest/stats | jq'
alias omni-freshness='curl -sf http://omni-knowledge-freshness:9430/freshness | jq ".[] | {source: .source_name, score: .freshness_score, last_ingested: .last_ingested}" | head -50'
alias omni-stale='curl -sf http://omni-knowledge-freshness:9430/freshness/stale | jq'
omni-ingest() { curl -sf -X POST http://omni-knowledge-ingestor:9420/ingest/repository -H "Content-Type: application/json" -d "{\"source_url\": \"$1\", \"source_name\": \"$2\", \"source_category\": \"${3:-general}\"}" | jq; }
omni-search-knowledge() { curl -sf -X POST http://omni-meilisearch-indexer:7701/search -H "Content-Type: application/json" -d "{\"query\": \"$1\", \"indexes\": [\"all\"], \"limit\": ${2:-10}}" | jq; }
omni-patterns() { curl -sf -X POST http://omni-neo4j-pattern-api:7475/patterns/recommend -H "Content-Type: application/json" -d "{\"task_description\": \"$1\", \"language\": \"${2:-python}\"}" | jq; }

alias omni-automations='curl -sf http://omni-n8n:5678/api/v1/workflows -H "X-N8N-API-KEY: ${N8N_API_KEY}" | jq ".data[] | {id: .id, name: .name, active: .active}"'
omni-automate() { echo "Creating automation: $1"; curl -sf -X POST http://omni-mcp-automation:8337/tools/create_automation -H "Content-Type: application/json" -d "{\"description\": \"$1\", \"activate\": true}" | jq; }

alias omni-revenue='curl -sf http://omni-crm-sync:3001/crm/pipeline-summary | jq'
alias omni-forecast='curl -sf http://omni-crm-sync:3001/crm/revenue-forecast | jq'
alias omni-invoices='curl -sf http://omni-invoice-generator:81/invoices/summary | jq'
alias omni-overdue='curl -sf http://omni-invoice-generator:81/invoices/overdue | jq'
alias omni-costs='curl -sf http://omni-litellm-cost-tracker:4001/costs/today | jq'

omni-restart() { curl -sf -X POST http://omni-orchestrator:9500/api/v1/action/restart -H "Content-Type: application/json" -d "{\"container\": \"omni-$1\"}" | jq; }
alias omni-backup='curl -sf -X POST http://omni-backup-orchestrator:8000/backup/all | jq'
omni-deploy() { curl -sf -X POST http://omni-orchestrator:9500/api/v1/action/deploy -H "Content-Type: application/json" -d "{\"app\": \"$1\", \"environment\": \"${2:-staging}\"}" | jq; }
alias omni-rotate='curl -sf -X POST http://omni-secret-rotation:9331/rotation/trigger-all-overdue | jq'

omni-logs() { docker logs --tail ${2:-100} -f "omni-$1"; }
omni-exec() { docker exec -it "omni-$1" "${@:2}"; }
alias omni-containers='docker ps --filter "label=omni.quantum.component" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | sort'
alias omni-docker='curl -sf http://omni-orchestrator:9500/api/v1/docker/stats | jq'

omni-help() {
  cat <<'HELP'
⚛️  Omni Quantum Elite — Command Reference
Use: omni-status, omni-health, omni-build, omni-models, omni-knowledge, omni-automate, omni-revenue, omni-logs ...
HELP
}

echo ""
echo "⚛️  Omni Quantum Elite — Command Center Ready"
echo "   Type 'omni-help' for all commands"
echo ""
