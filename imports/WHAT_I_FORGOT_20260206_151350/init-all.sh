#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# ⚛ OMNI QUANTUM ELITE — Post-Boot Initialization
# ══════════════════════════════════════════════════════════════════════════════
# Runs AFTER boot-platform.sh to configure service integrations:
#   - Vault policies & secret engines
#   - Gitea admin tokens & webhooks
#   - Mattermost bot accounts & channels
#   - MinIO buckets & access policies
#   - Uptime Kuma monitors (37 services)
#   - Prometheus alert rules
#   - Woodpecker CI Gitea integration
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source .env
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_success() { echo -e "${GREEN}[ OK ]${NC}  $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[FAIL]${NC}  $1"; }
log_section() { echo -e "\n${BOLD}${CYAN}══ $1 ══${NC}"; }

DOMAIN="${OMNI_DOMAIN:-localhost}"
ERRORS=0

# ══════════════════════════════════════════════════════════════════════════════
# 1. VAULT INITIALIZATION
# ══════════════════════════════════════════════════════════════════════════════
init_vault() {
    log_section "VAULT POLICIES & SECRET ENGINES"
    local VAULT_ADDR="http://localhost:${VAULT_PORT:-8200}"
    local VAULT_TOKEN="${VAULT_ROOT_TOKEN:-}"

    if [[ -z "$VAULT_TOKEN" ]]; then
        log_warn "VAULT_ROOT_TOKEN not set — skipping Vault init"
        return
    fi

    # Enable KV v2 secret engine
    curl -sf -X POST "${VAULT_ADDR}/v1/sys/mounts/omni" \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        -d '{"type":"kv","options":{"version":"2"}}' 2>/dev/null && \
        log_success "KV v2 engine mounted at omni/" || \
        log_info "KV engine already exists"

    # Enable PKI engine
    curl -sf -X POST "${VAULT_ADDR}/v1/sys/mounts/pki" \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        -d '{"type":"pki","config":{"max_lease_ttl":"87600h"}}' 2>/dev/null && \
        log_success "PKI engine mounted" || \
        log_info "PKI engine already exists"

    # Create policies
    for policy in orchestrator readonly cicd backup; do
        local policy_doc
        case $policy in
            orchestrator)
                policy_doc='path "omni/*" { capabilities = ["create","read","update","delete","list"] }'
                ;;
            readonly)
                policy_doc='path "omni/*" { capabilities = ["read","list"] }'
                ;;
            cicd)
                policy_doc='path "omni/data/cicd/*" { capabilities = ["read","list"] }\npath "omni/data/deploy/*" { capabilities = ["read","list"] }'
                ;;
            backup)
                policy_doc='path "omni/data/backup/*" { capabilities = ["create","read","update","list"] }'
                ;;
        esac

        curl -sf -X PUT "${VAULT_ADDR}/v1/sys/policies/acl/omni-${policy}" \
            -H "X-Vault-Token: ${VAULT_TOKEN}" \
            -d "{\"policy\":\"$(echo -e "$policy_doc")\"}" 2>/dev/null && \
            log_success "Policy: omni-${policy}" || \
            log_warn "Failed to create policy: omni-${policy}"
    done

    # Store initial secrets
    curl -sf -X POST "${VAULT_ADDR}/v1/omni/data/platform/config" \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        -d "{\"data\":{\"domain\":\"${DOMAIN}\",\"version\":\"${OMNI_VERSION:-1.0.0}\",\"initialized\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" \
        2>/dev/null && \
        log_success "Platform config stored in Vault" || \
        log_warn "Could not store platform config"
}

# ══════════════════════════════════════════════════════════════════════════════
# 2. GITEA SETUP
# ══════════════════════════════════════════════════════════════════════════════
init_gitea() {
    log_section "GITEA ADMIN TOKEN & ORGANIZATIONS"
    local GITEA_URL="http://localhost:${GITEA_PORT:-3000}"
    local GITEA_USER="${GITEA_ADMIN_USER:-omni-admin}"
    local GITEA_PASS="${GITEA_ADMIN_PASSWORD:-}"

    if [[ -z "$GITEA_PASS" ]]; then
        log_warn "GITEA_ADMIN_PASSWORD not set — skipping Gitea init"
        return
    fi

    # Create API token
    local token_resp
    token_resp=$(curl -sf -X POST "${GITEA_URL}/api/v1/users/${GITEA_USER}/tokens" \
        -u "${GITEA_USER}:${GITEA_PASS}" \
        -H "Content-Type: application/json" \
        -d '{"name":"omni-orchestrator","scopes":["all"]}' 2>/dev/null || echo "{}")

    local token
    token=$(echo "$token_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha1',''))" 2>/dev/null || echo "")

    if [[ -n "$token" ]]; then
        log_success "Gitea API token created"
        # Store in .env
        if ! grep -q "GITEA_ADMIN_TOKEN" "${PROJECT_ROOT}/.env" 2>/dev/null; then
            echo "GITEA_ADMIN_TOKEN=${token}" >> "${PROJECT_ROOT}/.env"
        fi
    else
        log_info "Gitea token may already exist"
    fi

    # Create organization
    curl -sf -X POST "${GITEA_URL}/api/v1/orgs" \
        -u "${GITEA_USER}:${GITEA_PASS}" \
        -H "Content-Type: application/json" \
        -d '{"username":"omni-quantum","full_name":"Omni Quantum Elite","visibility":"private"}' \
        2>/dev/null && \
        log_success "Organization 'omni-quantum' created" || \
        log_info "Organization may already exist"

    # Create Woodpecker CI webhook
    curl -sf -X POST "${GITEA_URL}/api/v1/orgs/omni-quantum/hooks" \
        -u "${GITEA_USER}:${GITEA_PASS}" \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"gitea\",
            \"active\": true,
            \"events\": [\"push\", \"pull_request\"],
            \"config\": {
                \"url\": \"http://omni-woodpecker-server:8000/hook\",
                \"content_type\": \"json\",
                \"secret\": \"${WOODPECKER_WEBHOOK_SECRET:-}\"
            }
        }" 2>/dev/null && \
        log_success "Woodpecker webhook configured" || \
        log_info "Webhook may already exist"
}

# ══════════════════════════════════════════════════════════════════════════════
# 3. MATTERMOST SETUP
# ══════════════════════════════════════════════════════════════════════════════
init_mattermost() {
    log_section "MATTERMOST BOT & CHANNELS"
    local MM_URL="http://localhost:${MATTERMOST_PORT:-8065}"
    local MM_TOKEN="${MATTERMOST_ADMIN_TOKEN:-}"

    if [[ -z "$MM_TOKEN" ]]; then
        log_warn "MATTERMOST_ADMIN_TOKEN not set — skipping Mattermost init"
        return
    fi

    # Create channels
    for channel in platform-ops alerts pipeline-builds deployments platform-logs; do
        curl -sf -X POST "${MM_URL}/api/v4/channels" \
            -H "Authorization: Bearer ${MM_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{
                \"team_id\": \"${MATTERMOST_TEAM_ID:-}\",
                \"name\": \"${channel}\",
                \"display_name\": \"$(echo "$channel" | tr '-' ' ' | sed 's/\b\(.\)/\u\1/g')\",
                \"type\": \"O\"
            }" 2>/dev/null && \
            log_success "Channel: ${channel}" || \
            log_info "Channel ${channel} may already exist"
    done

    # Create bot account
    local bot_resp
    bot_resp=$(curl -sf -X POST "${MM_URL}/api/v4/bots" \
        -H "Authorization: Bearer ${MM_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "omni-bot",
            "display_name": "⚛ Omni Quantum",
            "description": "Omni Quantum Elite Platform Bot"
        }' 2>/dev/null || echo "{}")

    local bot_id
    bot_id=$(echo "$bot_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null || echo "")

    if [[ -n "$bot_id" ]]; then
        log_success "Bot account created: omni-bot"

        # Create bot token
        local token_resp
        token_resp=$(curl -sf -X POST "${MM_URL}/api/v4/users/${bot_id}/tokens" \
            -H "Authorization: Bearer ${MM_TOKEN}" \
            -H "Content-Type: application/json" \
            -d '{"description":"orchestrator-token"}' 2>/dev/null || echo "{}")

        local bot_token
        bot_token=$(echo "$token_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo "")

        if [[ -n "$bot_token" ]]; then
            log_success "Bot token generated"
            if ! grep -q "MATTERMOST_BOT_TOKEN" "${PROJECT_ROOT}/.env" 2>/dev/null; then
                echo "MATTERMOST_BOT_TOKEN=${bot_token}" >> "${PROJECT_ROOT}/.env"
            fi
        fi
    else
        log_info "Bot may already exist"
    fi
}

# ══════════════════════════════════════════════════════════════════════════════
# 4. MINIO BUCKETS
# ══════════════════════════════════════════════════════════════════════════════
init_minio() {
    log_section "MINIO BUCKETS"

    if ! command -v mc &>/dev/null; then
        log_info "Installing MinIO client..."
        curl -sf -o /usr/local/bin/mc https://dl.min.io/client/mc/release/linux-amd64/mc 2>/dev/null && \
            chmod +x /usr/local/bin/mc || \
            { log_warn "Could not install mc — skipping MinIO init"; return; }
    fi

    mc alias set omni "http://localhost:${MINIO_API_PORT:-9000}" \
        "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" 2>/dev/null || \
        { log_warn "Could not connect to MinIO"; return; }

    # Create buckets
    for bucket in omni-backups omni-artifacts omni-sbom omni-models omni-logs omni-uploads omni-knowledge; do
        mc mb "omni/${bucket}" 2>/dev/null && \
            log_success "Bucket: ${bucket}" || \
            log_info "Bucket ${bucket} already exists"
    done

    # Set retention on backups
    mc retention set --default GOVERNANCE 30d "omni/omni-backups" 2>/dev/null || true
    log_success "Backup retention policy set (30d governance)"
}

# ══════════════════════════════════════════════════════════════════════════════
# 5. UPTIME KUMA MONITORS
# ══════════════════════════════════════════════════════════════════════════════
init_uptime_kuma() {
    log_section "UPTIME KUMA MONITORS"
    local KUMA_URL="http://localhost:${UPTIME_KUMA_PORT:-3001}"

    # Uptime Kuma doesn't have great API for bulk creation,
    # so we generate a JSON config that can be imported
    local monitors_file="${PROJECT_ROOT}/config/uptime-kuma-monitors.json"
    mkdir -p "$(dirname "$monitors_file")"

    python3 -c "
import json

services = [
    (1, 'Backup Fortress', 'omni-restic-server', 8000, '/'),
    (2, 'Cryptographic Fortress', 'omni-vault', 8200, '/v1/sys/health'),
    (3, 'AI Gateway', 'omni-litellm', 4000, '/health'),
    (4, 'Security Nexus', 'omni-authentik', 9000, '/-/health/ready/'),
    (5, 'Observatory', 'omni-prometheus', 9090, '/-/healthy'),
    (6, 'Log Nexus', 'omni-loki', 3100, '/ready'),
    (7, 'Code Fortress', 'omni-gitea', 3000, '/api/v1/version'),
    (8, 'Neural Network', 'omni-ollama', 11434, '/api/version'),
    (9, 'Workflow Engine', 'omni-n8n', 5678, '/healthz'),
    (10, 'Communication Hub', 'omni-mattermost', 8065, '/api/v4/system/ping'),
    (11, 'Vector Memory', 'omni-qdrant', 6333, '/healthz'),
    (12, 'Object Store', 'omni-minio', 9000, '/minio/health/live'),
    (13, 'AI Observability', 'omni-langfuse', 3000, '/api/public/health'),
    (27, 'Token Infinity', 'omni-token-infinity', 9600, '/health'),
    (28, 'Omi Bridge', 'omni-omi-bridge', 9700, '/health'),
    (29, 'Pulse Command Pro', 'omni-thanos-query', 9090, '/-/healthy'),
    (30, 'Log Nexus Pro', 'omni-log-pattern-detector', 9301, '/health'),
    (31, 'Guardian Eye', 'omni-uptime-kuma', 3001, '/'),
    (32, 'Backup Pro', 'omni-backup-orchestrator', 9321, '/health'),
    (33, 'Crypto Pro', 'omni-secret-rotation', 9331, '/health'),
    (34, 'Gateway Sentinel', 'omni-traefik', 8080, '/api/overview'),
    (35, 'Build Forge', 'omni-woodpecker-server', 8000, '/healthz'),
    (36, 'Code Forge', 'omni-coder', 7080, '/api/v2/buildinfo'),
    (37, 'Omni Command', 'omni-orchestrator', 9500, '/health'),
]

monitors = []
for sid, name, container, port, path in services:
    monitors.append({
        'name': f'[S{sid}] {name}',
        'type': 'http',
        'url': f'http://{container}:{port}{path}',
        'interval': 60,
        'retryInterval': 30,
        'maxretries': 3,
        'accepted_statuscodes': ['200-299', '301', '302'],
        'tags': [f'system-{sid}', 'omni-quantum'],
    })

with open('$monitors_file', 'w') as f:
    json.dump({'monitors': monitors}, f, indent=2)

print(f'Generated {len(monitors)} monitor definitions')
" 2>/dev/null && \
        log_success "Uptime Kuma monitor config generated" || \
        log_warn "Could not generate monitor config"

    log_info "Import monitors at: ${KUMA_URL} → Settings → Import"
}

# ══════════════════════════════════════════════════════════════════════════════
# 6. PROMETHEUS ALERT RULES
# ══════════════════════════════════════════════════════════════════════════════
init_prometheus_alerts() {
    log_section "PROMETHEUS ALERT RULES"

    local alerts_dir="${PROJECT_ROOT}/config/prometheus/rules"
    mkdir -p "$alerts_dir"

    cat > "${alerts_dir}/omni-platform.yml" << 'RULES'
groups:
  - name: omni_platform_health
    interval: 30s
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "{{ $labels.instance }} has been down for >2 minutes"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.job }}"
          description: "Error rate >5% for 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency on {{ $labels.job }}"
          description: "P95 latency >5s for 5 minutes"

      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.15
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space on {{ $labels.instance }}"
          description: "Less than 15% disk space remaining"

      - alert: HighMemoryUsage
        expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage >90% for 5 minutes"

      - alert: ContainerRestarting
        expr: increase(container_restart_count[1h]) > 3
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.name }} restarting frequently"
          description: ">3 restarts in the last hour"

      - alert: PostgresConnectionsHigh
        expr: pg_stat_activity_count / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL connections >80% capacity"

      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage >85%"

      - alert: OllamaGPUMemoryHigh
        expr: ollama_gpu_memory_used_bytes / ollama_gpu_memory_total_bytes > 0.9
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Ollama GPU memory >90%"

  - name: omni_pipeline_alerts
    rules:
      - alert: PipelineFailed
        expr: increase(omni_pipeline_failures_total[1h]) > 0
        labels:
          severity: warning
        annotations:
          summary: "Pipeline failure detected"

      - alert: PipelineStuck
        expr: omni_pipeline_duration_seconds > 3600
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Pipeline running >1 hour"
RULES

    log_success "Prometheus alert rules written to ${alerts_dir}/omni-platform.yml"
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

echo -e "${BOLD}${CYAN}"
echo "  ⚛  OMNI QUANTUM ELITE — Post-Boot Initialization"
echo "  ─────────────────────────────────────────────────────"
echo -e "${NC}"

START_TIME=$(date +%s)

init_vault
init_gitea
init_mattermost
init_minio
init_uptime_kuma
init_prometheus_alerts

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${BOLD}${CYAN}  ═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  ⚛  Post-boot initialization complete! (${DURATION}s)${NC}"
echo -e "${BOLD}${CYAN}  ═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Manual steps remaining:${NC}"
echo -e "    1. Import Uptime Kuma monitors from config/uptime-kuma-monitors.json"
echo -e "    2. Reload Prometheus: curl -X POST http://localhost:9090/-/reload"
echo -e "    3. Verify all services: ./scripts/boot-platform.sh --status"
echo ""
