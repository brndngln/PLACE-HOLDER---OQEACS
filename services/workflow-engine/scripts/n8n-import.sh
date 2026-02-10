#!/usr/bin/env bash
###############################################################################
# SYSTEM 9 — WORKFLOW ENGINE: n8n Workflow Importer
# Omni Quantum Elite AI Coding System — Communication & Workflow Layer
#
# Waits for n8n health, imports all workflow JSON files via REST API,
# activates each workflow, and verifies activation.
###############################################################################
set -euo pipefail

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
N8N_URL="${N8N_URL:-http://omni-n8n:5678}"
N8N_API_KEY="${N8N_API_KEY:-}"
WORKFLOWS_DIR="${WORKFLOWS_DIR:-$(dirname "$0")/../workflows}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log_info()  { echo "{\"level\":\"info\",\"service\":\"n8n-import\",\"system\":\"9\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}"; }
log_error() { echo "{\"level\":\"error\",\"service\":\"n8n-import\",\"system\":\"9\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}" >&2; }
log_warn()  { echo "{\"level\":\"warn\",\"service\":\"n8n-import\",\"system\":\"9\",\"msg\":\"$*\",\"ts\":\"$(date -u +%FT%TZ)\"}"; }

n8n_api() {
    local method="$1" path="$2"; shift 2
    curl -sf -X "$method" \
        -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
        -H "Content-Type: application/json" \
        "${N8N_URL}/api/v1${path}" "$@"
}

# ---------------------------------------------------------------------------
# Wait for n8n
# ---------------------------------------------------------------------------
wait_for_n8n() {
    log_info "Waiting for n8n at ${N8N_URL} ..."
    local retries=0 max_retries=60
    while [ "$retries" -lt "$max_retries" ]; do
        if curl -sf "${N8N_URL}/healthz" >/dev/null 2>&1; then
            log_info "n8n is healthy"
            return 0
        fi
        retries=$((retries + 1))
        sleep 5
    done
    log_error "n8n did not become healthy after $((max_retries * 5))s"
    exit 1
}

# ---------------------------------------------------------------------------
# Import workflows
# ---------------------------------------------------------------------------
import_workflows() {
    log_info "Importing workflows from ${WORKFLOWS_DIR} ..."

    local imported=0 failed=0

    for wf_file in "${WORKFLOWS_DIR}"/*.json; do
        [ -f "$wf_file" ] || continue
        local filename
        filename=$(basename "$wf_file")
        local wf_name
        wf_name=$(python3 -c "import json; print(json.load(open('${wf_file}'))['name'])" 2>/dev/null || echo "${filename%.json}")

        log_info "Importing workflow: ${wf_name} (${filename}) ..."

        local resp
        resp=$(n8n_api POST "/workflows" -d @"${wf_file}" 2>&1) || {
            log_warn "Import may have failed for ${wf_name}, checking if it already exists ..."
            # Check if workflow already exists by name
            local existing
            existing=$(n8n_api GET "/workflows" 2>/dev/null | python3 -c "
import sys, json
wfs = json.load(sys.stdin).get('data', [])
for wf in wfs:
    if wf['name'] == '${wf_name}':
        print(wf['id'])
        break
" 2>/dev/null || echo "")

            if [ -n "$existing" ]; then
                log_info "Workflow ${wf_name} already exists (ID: ${existing}), updating ..."
                n8n_api PUT "/workflows/${existing}" -d @"${wf_file}" 2>/dev/null || {
                    log_error "Failed to update workflow: ${wf_name}"
                    failed=$((failed + 1))
                    continue
                }
                resp="{\"id\":\"${existing}\"}"
            else
                log_error "Failed to import workflow: ${wf_name}"
                failed=$((failed + 1))
                continue
            fi
        }

        local wf_id
        wf_id=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

        if [ -n "$wf_id" ]; then
            imported=$((imported + 1))
            log_info "Workflow imported: ${wf_name} (ID: ${wf_id})"
        else
            log_error "Failed to extract workflow ID for: ${wf_name}"
            failed=$((failed + 1))
        fi
    done

    log_info "Import complete: ${imported} imported, ${failed} failed"
    echo "$imported"
}

# ---------------------------------------------------------------------------
# Activate all workflows
# ---------------------------------------------------------------------------
activate_workflows() {
    log_info "Activating all workflows ..."

    local workflows
    workflows=$(n8n_api GET "/workflows" 2>/dev/null || echo "{}")
    local wf_ids
    wf_ids=$(echo "$workflows" | python3 -c "
import sys, json
data = json.load(sys.stdin)
wfs = data.get('data', data) if isinstance(data, dict) else data
for wf in (wfs if isinstance(wfs, list) else []):
    print(wf['id'])
" 2>/dev/null || echo "")

    local activated=0
    for wf_id in $wf_ids; do
        [ -z "$wf_id" ] && continue
        n8n_api PATCH "/workflows/${wf_id}" -d '{"active": true}' >/dev/null 2>&1 && {
            activated=$((activated + 1))
            log_info "Activated workflow: ${wf_id}"
        } || {
            log_warn "Could not activate workflow: ${wf_id}"
        }
    done

    log_info "Activation complete: ${activated} workflows activated"
}

# ---------------------------------------------------------------------------
# Verify activation
# ---------------------------------------------------------------------------
verify_workflows() {
    log_info "Verifying workflow activation ..."

    local workflows
    workflows=$(n8n_api GET "/workflows" 2>/dev/null || echo "{}")

    python3 -c "
import sys, json
data = json.load(sys.stdin)
wfs = data.get('data', data) if isinstance(data, dict) else data
wf_list = wfs if isinstance(wfs, list) else []
active = sum(1 for wf in wf_list if wf.get('active'))
total = len(wf_list)
print(json.dumps({
    'level': 'info',
    'service': 'n8n-import',
    'system': '9',
    'msg': f'Verification: {active}/{total} workflows active',
    'active': active,
    'total': total
}))
" <<< "$workflows"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    log_info "=== n8n Workflow Import ==="
    log_info "System 9 — Workflow Engine"

    wait_for_n8n

    local count
    count=$(import_workflows)

    activate_workflows
    verify_workflows

    log_info "=== n8n import complete: ${count} workflows processed ==="
}

main "$@"
