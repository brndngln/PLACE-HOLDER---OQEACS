#!/usr/bin/env bash
# ===========================================================================
# SYSTEM 1 -- BACKUP FORTRESS: Initialization Script
# Omni Quantum Elite AI Coding System -- Data Protection Layer
#
# Creates MinIO buckets per backup target, initializes Restic repositories,
# verifies target service connectivity, and registers with System 37
# (Master Orchestrator) and System 31 (Uptime Kuma).
# ===========================================================================

set -euo pipefail

# ───────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://omni-minio:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_MC_ALIAS="${MINIO_MC_ALIAS:-omni}"

RESTIC_PASSWORD="${RESTIC_PASSWORD:-omni-quantum-restic-key}"

POSTGRES_HOST="${POSTGRES_HOST:-omni-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

REDIS_HOST="${REDIS_HOST:-omni-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

QDRANT_HOST="${QDRANT_HOST:-omni-qdrant}"
QDRANT_PORT="${QDRANT_PORT:-6333}"

VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"

GITEA_HOST="${GITEA_HOST:-omni-gitea}"
N8N_HOST="${N8N_HOST:-http://omni-n8n:5678}"
MATTERMOST_HOST="${MATTERMOST_HOST:-omni-mattermost}"
GRAFANA_HOST="${GRAFANA_HOST:-http://omni-grafana:3000}"
PROMETHEUS_HOST="${PROMETHEUS_HOST:-http://omni-prometheus:9090}"

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://omni-master-orchestrator:8000}"
UPTIME_KUMA_URL="${UPTIME_KUMA_URL:-http://omni-uptime-kuma:3001}"
UPTIME_KUMA_API_KEY="${UPTIME_KUMA_API_KEY:-}"

MAX_RETRIES="${MAX_RETRIES:-30}"
RETRY_INTERVAL="${RETRY_INTERVAL:-5}"

# Backup targets — each gets its own MinIO bucket and Restic repo
BACKUP_TARGETS=(
    "postgresql"
    "redis"
    "qdrant"
    "gitea"
    "vault"
    "minio"
    "docker_volumes"
    "n8n"
    "mattermost"
    "grafana"
    "prometheus"
)

# ───────────────────────────────────────────────────────────────────────
# Colors & Logging Helpers
# ───────────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')]${NC} $*"
}

log_ok() {
    echo -e "${BLUE}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')]${NC} ${GREEN}OK${NC} $*"
}

log_warn() {
    echo -e "${BLUE}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')]${NC} ${YELLOW}WARN${NC} $*" >&2
}

log_error() {
    echo -e "${BLUE}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')]${NC} ${RED}ERROR${NC} $*" >&2
}

log_step() {
    echo -e "${BLUE}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')]${NC} ${CYAN}==>${NC} $*"
}

# ───────────────────────────────────────────────────────────────────────
# Cleanup Trap
# ───────────────────────────────────────────────────────────────────────

cleanup() {
    local exit_code=$?
    if [ "$exit_code" -ne 0 ]; then
        log_error "Initialization failed with exit code ${exit_code}"
        log_error "Check the output above for details"
    fi
    exit "$exit_code"
}

trap cleanup EXIT

# ───────────────────────────────────────────────────────────────────────
# Step 1: Wait for MinIO to be available
# ───────────────────────────────────────────────────────────────────────

wait_for_minio() {
    log_step "Step 1: Waiting for MinIO at ${MINIO_ENDPOINT} ..."
    local attempt=0
    while [ "$attempt" -lt "$MAX_RETRIES" ]; do
        attempt=$((attempt + 1))
        if curl -sf "${MINIO_ENDPOINT}/minio/health/live" > /dev/null 2>&1; then
            log_ok "MinIO is healthy (attempt ${attempt})"
            return 0
        fi
        log "  attempt ${attempt}/${MAX_RETRIES} -- retrying in ${RETRY_INTERVAL}s"
        sleep "$RETRY_INTERVAL"
    done
    log_error "MinIO did not become healthy in time"
    exit 1
}

# ───────────────────────────────────────────────────────────────────────
# Step 2: Configure mc (MinIO Client) alias
# ───────────────────────────────────────────────────────────────────────

configure_mc() {
    log_step "Step 2: Configuring MinIO Client alias '${MINIO_MC_ALIAS}' ..."
    mc alias set "${MINIO_MC_ALIAS}" "${MINIO_ENDPOINT}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" > /dev/null 2>&1
    if mc admin info "${MINIO_MC_ALIAS}" > /dev/null 2>&1; then
        log_ok "mc alias configured and verified"
    else
        log_warn "mc alias set but admin info check failed (may lack admin perms)"
    fi
}

# ───────────────────────────────────────────────────────────────────────
# Step 3: Create MinIO buckets per backup target
# ───────────────────────────────────────────────────────────────────────

create_buckets() {
    log_step "Step 3: Creating MinIO buckets for backup targets ..."

    for target in "${BACKUP_TARGETS[@]}"; do
        local bucket_name="omni-backups-${target}"

        if mc ls "${MINIO_MC_ALIAS}/${bucket_name}" > /dev/null 2>&1; then
            log "  Bucket '${bucket_name}' already exists"
        else
            mc mb "${MINIO_MC_ALIAS}/${bucket_name}" > /dev/null 2>&1
            if [ $? -eq 0 ]; then
                log_ok "  Created bucket: ${bucket_name}"
            else
                log_error "  Failed to create bucket: ${bucket_name}"
                return 1
            fi
        fi

        # Set bucket versioning (for additional safety)
        mc version enable "${MINIO_MC_ALIAS}/${bucket_name}" > /dev/null 2>&1 || true
    done

    log_ok "All ${#BACKUP_TARGETS[@]} buckets created"
}

# ───────────────────────────────────────────────────────────────────────
# Step 4: Initialize Restic repositories
# ───────────────────────────────────────────────────────────────────────

init_restic_repos() {
    log_step "Step 4: Initializing Restic repositories ..."

    export AWS_ACCESS_KEY_ID="${MINIO_ACCESS_KEY}"
    export AWS_SECRET_ACCESS_KEY="${MINIO_SECRET_KEY}"
    export RESTIC_PASSWORD="${RESTIC_PASSWORD}"

    local initialized=0
    local skipped=0
    local failed=0

    for target in "${BACKUP_TARGETS[@]}"; do
        local repo="s3:${MINIO_ENDPOINT}/omni-backups-${target}"
        export RESTIC_REPOSITORY="${repo}"

        # Check if repo already initialized
        if restic snapshots > /dev/null 2>&1; then
            log "  Repo '${target}' already initialized"
            skipped=$((skipped + 1))
            continue
        fi

        # Initialize repository
        if restic init > /dev/null 2>&1; then
            log_ok "  Initialized Restic repo: ${repo}"
            initialized=$((initialized + 1))
        else
            log_error "  Failed to initialize Restic repo: ${repo}"
            failed=$((failed + 1))
        fi
    done

    log_ok "Restic repos: ${initialized} initialized, ${skipped} existing, ${failed} failed"

    if [ "$failed" -gt 0 ]; then
        log_warn "Some repositories failed to initialize"
    fi
}

# ───────────────────────────────────────────────────────────────────────
# Step 5: Verify target service connectivity
# ───────────────────────────────────────────────────────────────────────

verify_connectivity() {
    log_step "Step 5: Verifying target service connectivity ..."

    local reachable=0
    local unreachable=0

    # PostgreSQL
    if pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" > /dev/null 2>&1; then
        log_ok "  PostgreSQL: ${POSTGRES_HOST}:${POSTGRES_PORT} -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  PostgreSQL: ${POSTGRES_HOST}:${POSTGRES_PORT} -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    # Redis
    local redis_auth=""
    if [ -n "${REDIS_PASSWORD}" ]; then
        redis_auth="-a ${REDIS_PASSWORD}"
    fi
    if redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ${redis_auth} PING 2>/dev/null | grep -q "PONG"; then
        log_ok "  Redis: ${REDIS_HOST}:${REDIS_PORT} -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  Redis: ${REDIS_HOST}:${REDIS_PORT} -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    # Qdrant
    if curl -sf "http://${QDRANT_HOST}:${QDRANT_PORT}/healthz" > /dev/null 2>&1; then
        log_ok "  Qdrant: ${QDRANT_HOST}:${QDRANT_PORT} -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  Qdrant: ${QDRANT_HOST}:${QDRANT_PORT} -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    # Gitea
    if docker exec "${GITEA_HOST}" gitea --version > /dev/null 2>&1; then
        log_ok "  Gitea: container '${GITEA_HOST}' -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  Gitea: container '${GITEA_HOST}' -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    # Vault
    if curl -sf "${VAULT_ADDR}/v1/sys/health" > /dev/null 2>&1; then
        log_ok "  Vault: ${VAULT_ADDR} -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  Vault: ${VAULT_ADDR} -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    # MinIO (already verified in step 1, but double-check)
    if curl -sf "${MINIO_ENDPOINT}/minio/health/live" > /dev/null 2>&1; then
        log_ok "  MinIO: ${MINIO_ENDPOINT} -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  MinIO: ${MINIO_ENDPOINT} -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    # n8n
    if curl -sf "${N8N_HOST}/healthz" > /dev/null 2>&1; then
        log_ok "  n8n: ${N8N_HOST} -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  n8n: ${N8N_HOST} -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    # Mattermost
    if docker exec "${MATTERMOST_HOST}" mmctl version > /dev/null 2>&1; then
        log_ok "  Mattermost: container '${MATTERMOST_HOST}' -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  Mattermost: container '${MATTERMOST_HOST}' -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    # Grafana
    if curl -sf "${GRAFANA_HOST}/api/health" > /dev/null 2>&1; then
        log_ok "  Grafana: ${GRAFANA_HOST} -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  Grafana: ${GRAFANA_HOST} -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    # Prometheus
    if curl -sf "${PROMETHEUS_HOST}/-/healthy" > /dev/null 2>&1; then
        log_ok "  Prometheus: ${PROMETHEUS_HOST} -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  Prometheus: ${PROMETHEUS_HOST} -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    # Docker socket
    if docker info > /dev/null 2>&1; then
        log_ok "  Docker: socket accessible -- reachable"
        reachable=$((reachable + 1))
    else
        log_warn "  Docker: socket not accessible -- unreachable"
        unreachable=$((unreachable + 1))
    fi

    log "  Connectivity: ${reachable} reachable, ${unreachable} unreachable"

    if [ "$unreachable" -gt 0 ]; then
        log_warn "Some services are unreachable -- backups for those targets will fail until resolved"
    fi
}

# ───────────────────────────────────────────────────────────────────────
# Step 6: Register with System 37 Master Orchestrator
# ───────────────────────────────────────────────────────────────────────

register_orchestrator() {
    log_step "Step 6: Registering with System 37 Master Orchestrator ..."

    local registration_payload
    registration_payload=$(cat <<'PAYLOAD'
{
    "system_id": 1,
    "system_name": "backup-fortress",
    "services": [
        {
            "name": "backup-orchestrator",
            "url": "http://omni-backup-orchestrator:8000",
            "health_endpoint": "/health",
            "ready_endpoint": "/ready",
            "metrics_endpoint": "/metrics",
            "port": 8000,
            "critical": true
        },
        {
            "name": "restore-verifier",
            "url": "http://omni-restore-verifier:8001",
            "health_endpoint": "/health",
            "ready_endpoint": "/ready",
            "metrics_endpoint": "/metrics",
            "port": 8001,
            "critical": true
        }
    ],
    "description": "Restic-based backup orchestration and automated restore verification",
    "tier": "critical",
    "stack": "backup"
}
PAYLOAD
    )

    if curl -sf \
        -X POST \
        -H "Content-Type: application/json" \
        -d "${registration_payload}" \
        "${ORCHESTRATOR_URL}/api/v1/systems/register" > /dev/null 2>&1; then
        log_ok "Registered with System 37 Master Orchestrator"
    else
        log_warn "Could not register with System 37 (may not be running yet)"
    fi
}

# ───────────────────────────────────────────────────────────────────────
# Step 7: Register with System 31 Uptime Kuma
# ───────────────────────────────────────────────────────────────────────

register_uptime_kuma() {
    log_step "Step 7: Registering with System 31 Uptime Kuma ..."

    local monitors=(
        "backup-orchestrator|http://omni-backup-orchestrator:8000/health|Backup Orchestrator"
        "restore-verifier|http://omni-restore-verifier:8001/health|Restore Verifier"
    )

    for monitor_entry in "${monitors[@]}"; do
        IFS='|' read -r name url description <<< "${monitor_entry}"

        local monitor_payload
        monitor_payload=$(cat <<MONITOR
{
    "type": "http",
    "name": "System 1: ${description}",
    "url": "${url}",
    "method": "GET",
    "interval": 60,
    "retryInterval": 30,
    "maxretries": 3,
    "accepted_statuscodes": ["200-299"],
    "tags": [
        {"name": "system-1"},
        {"name": "backup-fortress"},
        {"name": "critical"}
    ]
}
MONITOR
        )

        if curl -sf \
            -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${UPTIME_KUMA_API_KEY}" \
            -d "${monitor_payload}" \
            "${UPTIME_KUMA_URL}/api/monitors" > /dev/null 2>&1; then
            log_ok "  Registered monitor: ${description}"
        else
            log_warn "  Could not register monitor: ${description} (Uptime Kuma may not be running)"
        fi
    done
}

# ───────────────────────────────────────────────────────────────────────
# Step 8: Verify Backup Orchestrator is running
# ───────────────────────────────────────────────────────────────────────

verify_orchestrator_health() {
    log_step "Step 8: Verifying Backup Fortress services ..."

    local orchestrator_ok=false
    local verifier_ok=false

    # Check backup orchestrator
    for attempt in $(seq 1 10); do
        if curl -sf "http://omni-backup-orchestrator:8000/health" > /dev/null 2>&1; then
            orchestrator_ok=true
            break
        fi
        sleep 3
    done

    if [ "$orchestrator_ok" = true ]; then
        log_ok "  Backup Orchestrator: healthy"
    else
        log_warn "  Backup Orchestrator: not yet responding"
    fi

    # Check restore verifier
    for attempt in $(seq 1 10); do
        if curl -sf "http://omni-restore-verifier:8001/health" > /dev/null 2>&1; then
            verifier_ok=true
            break
        fi
        sleep 3
    done

    if [ "$verifier_ok" = true ]; then
        log_ok "  Restore Verifier: healthy"
    else
        log_warn "  Restore Verifier: not yet responding"
    fi
}

# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────

main() {
    echo ""
    log "================================================================"
    log "${CYAN}SYSTEM 1 -- BACKUP FORTRESS: Initialization${NC}"
    log "================================================================"
    echo ""

    wait_for_minio
    configure_mc
    create_buckets
    init_restic_repos
    verify_connectivity
    register_orchestrator
    register_uptime_kuma
    verify_orchestrator_health

    echo ""
    log "================================================================"
    log "${GREEN}Backup Fortress initialization complete!${NC}"
    log "================================================================"
    log ""
    log "  Backup Targets:     ${#BACKUP_TARGETS[@]} configured"
    log "  MinIO Buckets:      omni-backups-{target} x ${#BACKUP_TARGETS[@]}"
    log "  Restic Repos:       s3:${MINIO_ENDPOINT}/omni-backups-{target}"
    log "  Orchestrator:       http://omni-backup-orchestrator:8000"
    log "  Verifier:           http://omni-restore-verifier:8001"
    log "  Metrics:            /metrics on both services"
    log ""
    log "  Default Schedule:"
    log "    PostgreSQL:       Every 6 hours"
    log "    Redis:            Every hour"
    log "    Qdrant:           Daily at 2AM"
    log "    Gitea:            Daily at 3AM"
    log "    Vault:            Daily at 1AM"
    log "    Everything else:  Daily at 4AM"
    log "    Retention prune:  Daily at 6AM"
    log "    Restore verify:   Daily at 5AM"
    log ""
    log "================================================================"
}

main "$@"
