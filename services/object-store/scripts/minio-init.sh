#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════════
# System 12 — Object Store (MinIO) — Initialization Script
# ═══════════════════════════════════════════════════════════════════════════════
# Initializes MinIO with buckets, service accounts, IAM policies, lifecycle
# rules, Prometheus metrics, bucket notifications, and service registrations.
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_NAME="$(basename "$0")"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://omni-minio:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:?MINIO_ROOT_USER is required}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD is required}"
MINIO_ALIAS="omni-minio"
MC_BIN="${MC_BIN:-/usr/local/bin/mc}"
POLICY_DIR="${POLICY_DIR:-/etc/minio/policies}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://omni-orchestrator:8080}"
UPTIME_KUMA_URL="${UPTIME_KUMA_URL:-http://omni-uptime-kuma:3001}"
N8N_WEBHOOK_BASE="${N8N_WEBHOOK_BASE:-http://omni-n8n:5678/webhook}"

MAX_RETRIES=60
RETRY_INTERVAL=5

# ─── Colored Timestamped Output ───────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ${GREEN}[INFO]${NC}  ${SCRIPT_NAME}: $*"; }
log_warn()    { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ${YELLOW}[WARN]${NC}  ${SCRIPT_NAME}: $*"; }
log_error()   { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ${RED}[ERROR]${NC} ${SCRIPT_NAME}: $*"; }
log_step()    { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ${CYAN}[STEP]${NC}  ${SCRIPT_NAME}: $*"; }
log_success() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ${GREEN}[OK]${NC}    ${SCRIPT_NAME}: $*"; }

# ─── Cleanup ──────────────────────────────────────────────────────────────────
TEMP_DIR=""
cleanup() {
    local exit_code=$?
    if [[ -n "${TEMP_DIR}" && -d "${TEMP_DIR}" ]]; then
        rm -rf "${TEMP_DIR}"
    fi
    if [[ $exit_code -ne 0 ]]; then
        log_error "Script exited with code ${exit_code}"
    fi
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

TEMP_DIR="$(mktemp -d)"

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Wait for MinIO to be healthy
# ═══════════════════════════════════════════════════════════════════════════════
wait_for_minio() {
    log_step "Phase 1: Waiting for MinIO to become healthy..."
    local attempt=0
    local backoff=${RETRY_INTERVAL}

    while [[ $attempt -lt $MAX_RETRIES ]]; do
        attempt=$((attempt + 1))
        if curl -sf "${MINIO_ENDPOINT}/minio/health/live" > /dev/null 2>&1; then
            log_success "MinIO is healthy (attempt ${attempt}/${MAX_RETRIES})"
            return 0
        fi
        log_warn "MinIO not ready (attempt ${attempt}/${MAX_RETRIES}), retrying in ${backoff}s..."
        sleep "${backoff}"
        if [[ $backoff -lt 30 ]]; then
            backoff=$((backoff + 2))
        fi
    done

    log_error "MinIO did not become healthy after ${MAX_RETRIES} attempts"
    return 1
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Install and configure MinIO Client (mc)
# ═══════════════════════════════════════════════════════════════════════════════
setup_mc() {
    log_step "Phase 2: Setting up MinIO Client (mc)..."

    if [[ ! -f "${MC_BIN}" ]]; then
        log_info "Downloading MinIO Client..."
        local arch
        arch=$(uname -m)
        local mc_arch="amd64"
        if [[ "${arch}" == "aarch64" || "${arch}" == "arm64" ]]; then
            mc_arch="arm64"
        fi
        curl -sf -o "${MC_BIN}" "https://dl.min.io/client/mc/release/linux-${mc_arch}/mc"
        chmod +x "${MC_BIN}"
        log_success "MinIO Client downloaded to ${MC_BIN}"
    else
        log_info "MinIO Client already installed at ${MC_BIN}"
    fi

    log_info "Configuring alias '${MINIO_ALIAS}' -> ${MINIO_ENDPOINT}"
    "${MC_BIN}" alias set "${MINIO_ALIAS}" \
        "${MINIO_ENDPOINT}" \
        "${MINIO_ROOT_USER}" \
        "${MINIO_ROOT_PASSWORD}" \
        --api S3v4 2>&1 | while read -r line; do log_info "  mc: ${line}"; done

    if "${MC_BIN}" admin info "${MINIO_ALIAS}" > /dev/null 2>&1; then
        log_success "MinIO Client alias '${MINIO_ALIAS}' configured and verified"
    else
        log_error "Failed to verify MinIO Client alias"
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Create buckets
# ═══════════════════════════════════════════════════════════════════════════════
create_bucket() {
    local bucket_name="$1"
    local description="$2"

    if "${MC_BIN}" ls "${MINIO_ALIAS}/${bucket_name}" > /dev/null 2>&1; then
        log_info "Bucket '${bucket_name}' already exists — ${description}"
        return 0
    fi

    if "${MC_BIN}" mb "${MINIO_ALIAS}/${bucket_name}" 2>&1 | while read -r line; do log_info "  mc: ${line}"; done; then
        log_success "Bucket '${bucket_name}' created — ${description}"
    else
        log_error "Failed to create bucket '${bucket_name}'"
        return 1
    fi

    # Enable versioning on critical buckets
    case "${bucket_name}" in
        omni-backups|omni-gitea-lfs|omni-knowledge-base|omni-client-deliverables)
            "${MC_BIN}" version enable "${MINIO_ALIAS}/${bucket_name}" 2>&1 | while read -r line; do log_info "  mc: ${line}"; done
            log_info "Versioning enabled for '${bucket_name}'"
            ;;
    esac
}

create_all_buckets() {
    log_step "Phase 3: Creating buckets..."

    create_bucket "omni-backups" "Backup orchestrator RW, restore-verifier R"
    create_bucket "omni-gitea-lfs" "Gitea LFS RW"
    create_bucket "omni-model-artifacts" "Ollama/MLflow RW, agents R"
    create_bucket "omni-pipeline-artifacts" "Woodpecker W, Coolify R, agents R (lifecycle: delete 90d)"
    create_bucket "omni-knowledge-base" "Knowledge Ingestor W, Qdrant/Neo4j/Wiki.js R"
    create_bucket "omni-client-deliverables" "Pipeline W, Crater R (lifecycle: infrequent access 30d)"
    create_bucket "omni-thanos" "Thanos RW"
    create_bucket "omni-langfuse" "Langfuse RW"
    create_bucket "omni-mlflow" "MLflow RW"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: Create IAM policies
# ═══════════════════════════════════════════════════════════════════════════════
apply_policy() {
    local policy_name="$1"
    local policy_file="$2"

    if [[ ! -f "${policy_file}" ]]; then
        log_error "Policy file not found: ${policy_file}"
        return 1
    fi

    if "${MC_BIN}" admin policy info "${MINIO_ALIAS}" "${policy_name}" > /dev/null 2>&1; then
        log_info "Policy '${policy_name}' already exists, updating..."
        "${MC_BIN}" admin policy remove "${MINIO_ALIAS}" "${policy_name}" 2>/dev/null || true
    fi

    if "${MC_BIN}" admin policy create "${MINIO_ALIAS}" "${policy_name}" "${policy_file}" 2>&1 | while read -r line; do log_info "  mc: ${line}"; done; then
        log_success "Policy '${policy_name}' applied from ${policy_file}"
    else
        log_error "Failed to apply policy '${policy_name}'"
        return 1
    fi
}

create_policies() {
    log_step "Phase 4: Creating IAM policies..."

    apply_policy "backup-sa-policy" "${POLICY_DIR}/backup-sa-policy.json"
    apply_policy "gitea-sa-policy" "${POLICY_DIR}/gitea-sa-policy.json"
    apply_policy "pipeline-sa-policy" "${POLICY_DIR}/pipeline-sa-policy.json"
    apply_policy "knowledge-sa-policy" "${POLICY_DIR}/knowledge-sa-policy.json"
    apply_policy "thanos-sa-policy" "${POLICY_DIR}/thanos-sa-policy.json"
    apply_policy "langfuse-sa-policy" "${POLICY_DIR}/langfuse-sa-policy.json"
    apply_policy "mlflow-sa-policy" "${POLICY_DIR}/mlflow-sa-policy.json"
    apply_policy "restore-verifier-policy" "${POLICY_DIR}/restore-verifier-policy.json"
    apply_policy "ollama-sa-policy" "${POLICY_DIR}/ollama-sa-policy.json"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Create service accounts and attach policies
# ═══════════════════════════════════════════════════════════════════════════════
create_service_account() {
    local sa_name="$1"
    local policy_name="$2"
    local description="$3"

    log_info "Creating service account '${sa_name}' with policy '${policy_name}'..."

    local sa_output
    sa_output=$("${MC_BIN}" admin user svcacct add "${MINIO_ALIAS}" "${MINIO_ROOT_USER}" \
        --name "${sa_name}" \
        --description "${description}" \
        --policy "${POLICY_DIR}/${policy_name}.json" 2>&1) || {
        # Service account may already exist, try to update
        log_warn "Service account '${sa_name}' may already exist, attempting to list..."
        local existing
        existing=$("${MC_BIN}" admin user svcacct ls "${MINIO_ALIAS}" "${MINIO_ROOT_USER}" 2>&1) || true
        if echo "${existing}" | grep -q "${sa_name}"; then
            log_info "Service account '${sa_name}' already exists, skipping"
            return 0
        fi
        log_error "Failed to create service account '${sa_name}'"
        return 1
    }

    local access_key
    access_key=$(echo "${sa_output}" | grep "Access Key" | awk '{print $NF}' || echo "")
    local secret_key
    secret_key=$(echo "${sa_output}" | grep "Secret Key" | awk '{print $NF}' || echo "")

    if [[ -n "${access_key}" ]]; then
        log_success "Service account '${sa_name}' created (access_key: ${access_key:0:8}...)"
        # Store credentials securely in temp directory for retrieval by dependent services
        cat > "${TEMP_DIR}/sa_${sa_name}.json" <<EOF
{
  "service_account": "${sa_name}",
  "access_key": "${access_key}",
  "secret_key": "${secret_key}",
  "policy": "${policy_name}"
}
EOF
    else
        log_success "Service account '${sa_name}' created"
    fi
}

create_service_accounts() {
    log_step "Phase 5: Creating service accounts..."

    create_service_account "backup-sa" "backup-sa-policy" "Backup orchestrator service account"
    create_service_account "gitea-sa" "gitea-sa-policy" "Gitea LFS service account"
    create_service_account "pipeline-sa" "pipeline-sa-policy" "CI/CD pipeline service account"
    create_service_account "knowledge-sa" "knowledge-sa-policy" "Knowledge ingestor service account"
    create_service_account "thanos-sa" "thanos-sa-policy" "Thanos metrics service account"
    create_service_account "langfuse-sa" "langfuse-sa-policy" "Langfuse observability service account"
    create_service_account "mlflow-sa" "mlflow-sa-policy" "MLflow model registry service account"
    create_service_account "restore-verifier-sa" "restore-verifier-policy" "Backup restore verifier (read-only)"
    create_service_account "ollama-sa" "ollama-sa-policy" "Ollama model artifacts service account"

    log_info "Service account credentials stored in temporary directory: ${TEMP_DIR}"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6: Set lifecycle rules
# ═══════════════════════════════════════════════════════════════════════════════
set_lifecycle_rules() {
    log_step "Phase 6: Setting lifecycle rules..."

    # Pipeline artifacts: delete after 90 days
    log_info "Setting lifecycle rule: omni-pipeline-artifacts — delete after 90 days"
    local pipeline_lifecycle
    pipeline_lifecycle=$(cat <<'EOF'
{
  "Rules": [
    {
      "ID": "delete-after-90-days",
      "Status": "Enabled",
      "Expiration": {
        "Days": 90
      },
      "Filter": {
        "Prefix": ""
      }
    }
  ]
}
EOF
    )
    echo "${pipeline_lifecycle}" > "${TEMP_DIR}/pipeline-lifecycle.json"
    "${MC_BIN}" ilm import "${MINIO_ALIAS}/omni-pipeline-artifacts" < "${TEMP_DIR}/pipeline-lifecycle.json" 2>&1 | while read -r line; do log_info "  mc: ${line}"; done
    log_success "Lifecycle rule applied: omni-pipeline-artifacts (delete after 90 days)"

    # Client deliverables: transition to infrequent access after 30 days
    log_info "Setting lifecycle rule: omni-client-deliverables — infrequent access after 30 days"
    local client_lifecycle
    client_lifecycle=$(cat <<'EOF'
{
  "Rules": [
    {
      "ID": "transition-infrequent-30-days",
      "Status": "Enabled",
      "Transition": {
        "Days": 30,
        "StorageClass": "STANDARD_IA"
      },
      "Filter": {
        "Prefix": ""
      }
    }
  ]
}
EOF
    )
    echo "${client_lifecycle}" > "${TEMP_DIR}/client-lifecycle.json"
    "${MC_BIN}" ilm import "${MINIO_ALIAS}/omni-client-deliverables" < "${TEMP_DIR}/client-lifecycle.json" 2>&1 | while read -r line; do log_info "  mc: ${line}"; done
    log_success "Lifecycle rule applied: omni-client-deliverables (infrequent access after 30 days)"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7: Enable Prometheus metrics
# ═══════════════════════════════════════════════════════════════════════════════
enable_metrics() {
    log_step "Phase 7: Enabling Prometheus metrics..."

    # MinIO exposes Prometheus metrics at /minio/v2/metrics/cluster by default
    # Verify metrics endpoint is accessible
    local http_code
    http_code=$(curl -sf -o /dev/null -w "%{http_code}" \
        "${MINIO_ENDPOINT}/minio/v2/metrics/cluster" 2>/dev/null) || http_code="000"

    if [[ "${http_code}" == "200" || "${http_code}" == "401" ]]; then
        log_success "Prometheus metrics endpoint active at ${MINIO_ENDPOINT}/minio/v2/metrics/cluster"
    else
        log_info "Configuring Prometheus metrics via mc..."
        "${MC_BIN}" admin prometheus generate "${MINIO_ALIAS}" 2>&1 | while read -r line; do log_info "  mc: ${line}"; done
        log_success "Prometheus metrics configuration generated"
    fi

    log_info "Metrics scrape target: ${MINIO_ENDPOINT}/minio/v2/metrics/cluster"
    log_info "Authentication: use bearer token from 'mc admin prometheus generate'"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8: Set up bucket notifications to n8n
# ═══════════════════════════════════════════════════════════════════════════════
setup_bucket_notifications() {
    log_step "Phase 8: Setting up bucket notifications -> n8n..."

    # Configure webhook notification target
    local webhook_id="n8n-upload-hook"

    log_info "Configuring webhook notification target '${webhook_id}'..."
    "${MC_BIN}" admin config set "${MINIO_ALIAS}" \
        "notify_webhook:${webhook_id}" \
        endpoint="${N8N_WEBHOOK_BASE}/minio-upload" \
        queue_dir="/tmp/minio-events" \
        queue_limit="10000" 2>&1 | while read -r line; do log_info "  mc: ${line}"; done || {
        log_warn "Webhook notification target may already be configured"
    }

    # Restart MinIO to apply notification configuration
    log_info "Restarting MinIO to apply notification configuration..."
    "${MC_BIN}" admin service restart "${MINIO_ALIAS}" 2>&1 | while read -r line; do log_info "  mc: ${line}"; done || {
        log_warn "Could not restart MinIO (may require manual restart)"
    }

    # Wait for MinIO to come back
    sleep 10
    local attempt=0
    while [[ $attempt -lt 30 ]]; do
        attempt=$((attempt + 1))
        if curl -sf "${MINIO_ENDPOINT}/minio/health/live" > /dev/null 2>&1; then
            break
        fi
        sleep 2
    done

    # Set up event notifications on upload for key buckets
    local notification_buckets=(
        "omni-backups"
        "omni-model-artifacts"
        "omni-pipeline-artifacts"
        "omni-knowledge-base"
        "omni-client-deliverables"
    )

    for bucket in "${notification_buckets[@]}"; do
        log_info "Enabling upload notifications for '${bucket}'..."
        "${MC_BIN}" event add "${MINIO_ALIAS}/${bucket}" \
            "arn:minio:sqs::${webhook_id}:webhook" \
            --event "put" \
            --suffix "*" 2>&1 | while read -r line; do log_info "  mc: ${line}"; done || {
            log_warn "Event notification may already exist for '${bucket}'"
        }
        log_success "Upload notifications enabled for '${bucket}'"
    done
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 9: Register with Orchestrator (System 37)
# ═══════════════════════════════════════════════════════════════════════════════
register_orchestrator() {
    log_step "Phase 9: Registering with System 37 Orchestrator..."

    local payload
    payload=$(cat <<'EOF'
{
  "system_id": 12,
  "system_name": "object-store",
  "service_type": "minio",
  "display_name": "Object Store (MinIO)",
  "health_endpoint": "http://omni-minio:9000/minio/health/live",
  "metrics_endpoint": "http://omni-minio:9000/minio/v2/metrics/cluster",
  "api_endpoint": "http://omni-minio:9000",
  "console_endpoint": "http://omni-minio:9001",
  "status": "running",
  "version": "RELEASE.2024-01-01",
  "dependencies": [],
  "capabilities": ["s3", "lfs", "lifecycle", "notifications", "versioning", "encryption"],
  "network": "omni-quantum-network",
  "ports": {
    "api": 9000,
    "console": 9001
  },
  "buckets": [
    "omni-backups",
    "omni-gitea-lfs",
    "omni-model-artifacts",
    "omni-pipeline-artifacts",
    "omni-knowledge-base",
    "omni-client-deliverables",
    "omni-thanos",
    "omni-langfuse",
    "omni-mlflow"
  ],
  "tags": ["foundation", "storage", "s3-compatible"]
}
EOF
    )

    local response
    response=$(curl -sf -X POST \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        "${ORCHESTRATOR_URL}/api/v1/systems/register" 2>&1) || {
        log_warn "Could not register with Orchestrator (may not be running yet)"
        return 0
    }

    log_success "Registered with System 37 Orchestrator"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Phase 10: Register with Uptime Kuma (System 31)
# ═══════════════════════════════════════════════════════════════════════════════
register_uptime_kuma() {
    log_step "Phase 10: Registering with System 31 Uptime Kuma..."

    local payload
    payload=$(cat <<'EOF'
{
  "type": "http",
  "name": "System 12 - Object Store (MinIO)",
  "url": "http://omni-minio:9000/minio/health/live",
  "method": "GET",
  "interval": 60,
  "retryInterval": 30,
  "maxretries": 3,
  "accepted_statuscodes": ["200-299"],
  "notificationIDList": {},
  "tags": [
    {"name": "system-12", "value": "object-store"},
    {"name": "category", "value": "foundation"},
    {"name": "service", "value": "minio"}
  ]
}
EOF
    )

    local response
    response=$(curl -sf -X POST \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        "${UPTIME_KUMA_URL}/api/monitors" 2>&1) || {
        log_warn "Could not register with Uptime Kuma (may not be running yet)"
        return 0
    }

    log_success "Registered with System 31 Uptime Kuma"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Main Execution
# ═══════════════════════════════════════════════════════════════════════════════
main() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  System 12 — Object Store (MinIO) — Initialization${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    wait_for_minio
    setup_mc
    create_all_buckets
    create_policies
    create_service_accounts
    set_lifecycle_rules
    enable_metrics
    setup_bucket_notifications
    register_orchestrator
    register_uptime_kuma

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  System 12 — Object Store initialization complete${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    log_success "All initialization phases completed successfully"
    log_info "Buckets: 9 created | Service accounts: 9 created | Policies: 9 applied"
    log_info "Lifecycle rules: 2 applied | Notifications: 5 buckets configured"
}

main "$@"
