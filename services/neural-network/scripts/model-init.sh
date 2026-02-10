#!/usr/bin/env bash
###############################################################################
# SYSTEM 8 — NEURAL NETWORK: Model Initialization
# Omni Quantum Elite AI Coding System — AI Coding Pipeline
#
# Wait for Ollama → auto-pull configured models → start model-manager →
# load by priority into VRAM budget → report to Mattermost → register.
###############################################################################
set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://omni-ollama:11434}"
MODEL_MANAGER_URL="${MODEL_MANAGER_URL:-http://localhost:11435}"
MATTERMOST_WEBHOOK="${MATTERMOST_WEBHOOK_URL:-http://omni-mattermost-webhook:8066}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://omni-orchestrator:9500}"
CONFIG_FILE="${MODELS_CONFIG:-/app/config/models-config.yaml}"

log_info()  { echo "{\"level\":\"info\",\"service\":\"model-init\",\"system\":\"8\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}"; }
log_error() { echo "{\"level\":\"error\",\"service\":\"model-init\",\"system\":\"8\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}" >&2; }

# ---------------------------------------------------------------------------
# Wait for Ollama
# ---------------------------------------------------------------------------
wait_for_ollama() {
    log_info "Waiting for Ollama at ${OLLAMA_URL} ..."
    local retries=0
    while [ "$retries" -lt 120 ]; do
        if curl -sf "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
            log_info "Ollama is healthy"
            return 0
        fi
        retries=$((retries + 1))
        sleep 5
    done
    log_error "Ollama did not become healthy"
    exit 1
}

# ---------------------------------------------------------------------------
# Auto-pull missing models
# ---------------------------------------------------------------------------
auto_pull_models() {
    log_info "Checking models for auto-pull ..."
    local available
    available=$(curl -sf "${OLLAMA_URL}/api/tags" | python3 -c "
import sys, json
models = json.load(sys.stdin).get('models', [])
for m in models:
    print(m.get('name', m.get('model', '')))
" 2>/dev/null || echo "")

    python3 -c "
import yaml, sys
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
available = set('''${available}'''.strip().split('\n'))
for m in cfg.get('models', []):
    if m.get('auto_pull') and m['name'] not in available:
        print(m['name'])
" 2>/dev/null | while read -r model_name; do
        [ -z "$model_name" ] && continue
        log_info "Pulling model: ${model_name} ..."
        curl -sf -X POST "${OLLAMA_URL}/api/pull" \
            -H "Content-Type: application/json" \
            -d "{\"name\":\"${model_name}\",\"stream\":false}" \
            --max-time 3600 >/dev/null 2>&1 && \
            log_info "Pulled: ${model_name}" || \
            log_error "Failed to pull: ${model_name}"
    done
}

# ---------------------------------------------------------------------------
# Wait for model-manager
# ---------------------------------------------------------------------------
wait_for_manager() {
    log_info "Waiting for model-manager ..."
    local retries=0
    while [ "$retries" -lt 60 ]; do
        if curl -sf "${MODEL_MANAGER_URL}/health" >/dev/null 2>&1; then
            log_info "Model manager is healthy"
            return 0
        fi
        retries=$((retries + 1))
        sleep 2
    done
    log_error "Model manager did not start"
    exit 1
}

# ---------------------------------------------------------------------------
# Load models by priority
# ---------------------------------------------------------------------------
load_models_by_priority() {
    log_info "Loading models by priority ..."
    local loaded=0
    python3 -c "
import yaml
with open('${CONFIG_FILE}') as f:
    cfg = yaml.safe_load(f) or {}
for m in sorted(cfg.get('models', []), key=lambda x: x.get('priority', 99)):
    print(m['name'])
" 2>/dev/null | while read -r model_name; do
        [ -z "$model_name" ] && continue
        log_info "Loading model: ${model_name} ..."
        local resp
        resp=$(curl -sf -X POST "${MODEL_MANAGER_URL}/models/load" \
            -H "Content-Type: application/json" \
            -d "{\"name\":\"${model_name}\"}" \
            --max-time 300 2>&1) && {
            loaded=$((loaded + 1))
            log_info "Loaded: ${model_name}"
        } || {
            log_info "Could not load ${model_name} (VRAM budget likely exhausted)"
            break
        }
    done
    echo "$loaded"
}

# ---------------------------------------------------------------------------
# Report & register
# ---------------------------------------------------------------------------
report_to_mattermost() {
    local loaded_models
    loaded_models=$(curl -sf "${MODEL_MANAGER_URL}/models" | python3 -c "
import sys, json
models = json.load(sys.stdin)
loaded = [m for m in models if m.get('status') == 'loaded']
lines = []
for m in loaded:
    lines.append(f\"  • {m['name']} (priority {m.get('priority', '?')})\")
print(f'Neural Network online — {len(loaded)} model(s) loaded:\n' + '\n'.join(lines))
" 2>/dev/null || echo "Neural Network initialized")

    curl -sf -X POST "${MATTERMOST_WEBHOOK}/webhook/knowledge" \
        -H "Content-Type: application/json" \
        -d "{\"source_name\":\"Neural Network\",\"status\":\"complete\",\"summary\":\"${loaded_models}\",\"docs_ingested\":0,\"embeddings_created\":0,\"staleness_score\":0,\"processing_time\":\"N/A\"}" \
        --max-time 5 >/dev/null 2>&1 || true
}

register_with_orchestrator() {
    curl -sf -X POST "${ORCHESTRATOR_URL}/api/services/register" \
        -H "Content-Type: application/json" \
        -d '{"name":"neural-network","system":8,"endpoint":"http://omni-model-manager:11435","health":"http://omni-model-manager:11435/health","tier":"high"}' \
        --max-time 5 >/dev/null 2>&1 || log_info "Orchestrator registration skipped"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    log_info "=== Neural Network Init (System 8) ==="
    wait_for_ollama
    auto_pull_models
    wait_for_manager
    load_models_by_priority
    report_to_mattermost
    register_with_orchestrator
    log_info "=== Neural Network init complete ==="
}

main "$@"
