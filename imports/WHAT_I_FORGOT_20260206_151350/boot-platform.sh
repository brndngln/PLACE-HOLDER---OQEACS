#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# ⚛ OMNI QUANTUM ELITE — TIERED BOOT ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
# Boots the entire 37-system platform in dependency order with health-check
# gates between each tier. Ensures services are healthy before starting
# dependent services.
#
# Usage:
#   ./boot-platform.sh                    # Full boot (all tiers)
#   ./boot-platform.sh --tier 0-3         # Boot tiers 0 through 3 only
#   ./boot-platform.sh --status           # Show status of all services
#   ./boot-platform.sh --shutdown         # Graceful shutdown (reverse order)
#   ./boot-platform.sh --restart <svc>    # Restart a specific service
#   ./boot-platform.sh --skip-health      # Boot without health checks
#   ./boot-platform.sh --dry-run          # Show what would be started
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_DIR="${PROJECT_ROOT}/compose"
LOG_DIR="${PROJECT_ROOT}/logs"
BOOT_LOG="${LOG_DIR}/boot-$(date +%Y%m%d-%H%M%S).log"

# Source .env
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# ─── Configuration ────────────────────────────────────────────────────────────
DOMAIN="${OMNI_DOMAIN:-localhost}"
HEALTH_TIMEOUT=120         # Max seconds to wait for a service health check
HEALTH_INTERVAL=3          # Seconds between health checks
DOCKER_COMPOSE="docker compose"
NETWORK_NAME="omni-quantum-network"

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; MAGENTA='\033[0;35m'
BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC}  $1" | tee -a "$BOOT_LOG"; }
log_success() { echo -e "${GREEN}[ OK ]${NC}  $1" | tee -a "$BOOT_LOG"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1" | tee -a "$BOOT_LOG"; }
log_error()   { echo -e "${RED}[FAIL]${NC}  $1" | tee -a "$BOOT_LOG"; }
log_tier()    { echo -e "\n${BOLD}${MAGENTA}━━━ TIER $1 ━━━${NC}" | tee -a "$BOOT_LOG"; }
log_dim()     { echo -e "${DIM}        $1${NC}" | tee -a "$BOOT_LOG"; }

# ─── Parse Arguments ──────────────────────────────────────────────────────────
MODE="boot"
TIER_RANGE=""
SKIP_HEALTH=false
DRY_RUN=false
RESTART_SVC=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --tier)       TIER_RANGE="$2"; shift 2 ;;
        --status)     MODE="status"; shift ;;
        --shutdown)   MODE="shutdown"; shift ;;
        --restart)    MODE="restart"; RESTART_SVC="$2"; shift 2 ;;
        --skip-health) SKIP_HEALTH=true; shift ;;
        --dry-run)    DRY_RUN=true; shift ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "  --tier 0-3       Boot specific tier range"
            echo "  --status         Show status of all services"
            echo "  --shutdown       Graceful shutdown (reverse order)"
            echo "  --restart <svc>  Restart a specific service"
            echo "  --skip-health    Skip health check gates"
            echo "  --dry-run        Show what would be started"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ─── Ensure log directory ────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"
touch "$BOOT_LOG"

# ══════════════════════════════════════════════════════════════════════════════
# SERVICE DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════
# Each tier is an array of "compose_file:service_name:container_name:health_url:health_type"
# health_type: http (HTTP 200), tcp (port open), pg (PostgreSQL), redis, cmd (custom command)

# ─── TIER 0: Storage & Network Foundation ─────────────────────────────────────
TIER_0=(
    "docker-compose.postgres.yml:postgres:omni-postgres:5432:pg"
    "docker-compose.redis.yml:redis:omni-redis:6379:redis"
    "docker-compose.minio.yml:minio:omni-minio:9000:http"
    "docker-compose.neo4j.yml:neo4j:omni-neo4j:7474:http"
)
TIER_0_NAME="Storage & Network Foundation"

# ─── TIER 1: Security & Observability ─────────────────────────────────────────
TIER_1=(
    "docker-compose.vault.yml:vault:omni-vault:8200:http"
    "docker-compose.traefik.yml:traefik:omni-traefik:8080:http"
    "docker-compose.authentik.yml:authentik-server:omni-authentik:9000:http"
    "docker-compose.prometheus.yml:prometheus:omni-prometheus:9090:http"
    "docker-compose.grafana.yml:grafana:omni-grafana:3000:http"
    "docker-compose.loki.yml:loki:omni-loki:3100:http"
)
TIER_1_NAME="Security & Observability"

# ─── TIER 2: AI & Core Development ───────────────────────────────────────────
TIER_2=(
    "docker-compose.ollama.yml:ollama:omni-ollama:11434:http"
    "docker-compose.litellm.yml:litellm:omni-litellm:4000:http"
    "docker-compose.gitea.yml:gitea:omni-gitea:3000:http"
    "docker-compose.mattermost.yml:mattermost:omni-mattermost:8065:http"
    "docker-compose.qdrant.yml:qdrant:omni-qdrant:6333:http"
    "docker-compose.langfuse.yml:langfuse:omni-langfuse:3000:http"
)
TIER_2_NAME="AI & Core Development"

# ─── TIER 3: Workflow & Business Tools ────────────────────────────────────────
TIER_3=(
    "docker-compose.n8n.yml:n8n:omni-n8n:5678:http"
    "docker-compose.nango.yml:nango:omni-nango:3003:http"
    "docker-compose.flowise.yml:flowise:omni-flowise:3000:http"
    "docker-compose.superset.yml:superset:omni-superset:8088:http"
    "docker-compose.calcom.yml:calcom:omni-calcom:3000:http"
    "docker-compose.crater.yml:crater:omni-crater:80:http"
    "docker-compose.crowdsec.yml:crowdsec:omni-crowdsec:8080:http"
    "docker-compose.portainer.yml:portainer:omni-portainer:9443:http"
)
TIER_3_NAME="Workflow & Business Tools"

# ─── TIER 4: AI Coding Engines ────────────────────────────────────────────────
TIER_4=(
    "docker-compose.openhands.yml:openhands:omni-openhands:3000:http"
    "docker-compose.swe-agent.yml:swe-agent:omni-swe-agent:8000:http"
    "docker-compose.token-infinity.yml:token-infinity:omni-token-infinity:9600:http"
    "docker-compose.omi-bridge.yml:omi-bridge:omni-omi-bridge:9700:http"
)
TIER_4_NAME="AI Coding Engines"

# ─── TIER 5: Enhanced Infrastructure (Systems 29-36) ─────────────────────────
TIER_5=(
    "docker-compose.system-29.yml:thanos-query:omni-thanos-query:9090:http"
    "docker-compose.system-30.yml:log-pattern-detector:omni-log-pattern-detector:9301:http"
    "docker-compose.system-31.yml:uptime-kuma:omni-uptime-kuma:3001:http"
    "docker-compose.system-32.yml:backup-orchestrator:omni-backup-orchestrator:9321:http"
    "docker-compose.system-33.yml:secret-rotation:omni-secret-rotation:9331:http"
    "docker-compose.system-34.yml:rate-limiter:omni-rate-limiter:9341:http"
    "docker-compose.system-35.yml:woodpecker-server:omni-woodpecker-server:8000:http"
    "docker-compose.system-36.yml:coder:omni-coder:7080:http"
)
TIER_5_NAME="Enhanced Infrastructure (Systems 29-36)"

# ─── TIER 6: Master Orchestrator (System 37 — CAPSTONE) ──────────────────────
TIER_6=(
    "docker-compose.system-37.yml:orchestrator-api:omni-orchestrator:9500:http"
)
TIER_6_NAME="Master Orchestrator (Capstone)"

# All tiers array
ALL_TIERS=("0" "1" "2" "3" "4" "5" "6")

# ══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

check_health_http() {
    local url="$1"
    curl -sf --max-time 5 "http://localhost:${url}" >/dev/null 2>&1 || \
    curl -sf --max-time 5 "http://${url}" >/dev/null 2>&1 || \
    curl -sfk --max-time 5 "https://localhost:${url}" >/dev/null 2>&1
}

check_health_tcp() {
    local port="$1"
    timeout 3 bash -c "echo >/dev/tcp/localhost/$port" 2>/dev/null
}

check_health_pg() {
    local port="$1"
    PGPASSWORD="${POSTGRES_SUPERUSER_PASSWORD:-}" pg_isready \
        -h localhost -p "$port" -U "${POSTGRES_SUPERUSER:-omni_admin}" >/dev/null 2>&1 || \
    check_health_tcp "$port"
}

check_health_redis() {
    local port="$1"
    redis-cli -h localhost -p "$port" -a "${REDIS_PASSWORD:-}" ping 2>/dev/null | grep -q PONG || \
    check_health_tcp "$port"
}

check_health() {
    local container="$1"
    local health_url="$2"
    local health_type="$3"

    # First try Docker's built-in health check
    local docker_health
    docker_health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
    if [[ "$docker_health" == "healthy" ]]; then
        return 0
    fi

    # Then try our custom checks
    case "$health_type" in
        http)  check_health_http "$health_url" ;;
        tcp)   check_health_tcp "$health_url" ;;
        pg)    check_health_pg "$health_url" ;;
        redis) check_health_redis "$health_url" ;;
        cmd)   docker exec "$container" $health_url >/dev/null 2>&1 ;;
        *)     check_health_tcp "$health_url" ;;
    esac
}

wait_for_health() {
    local container="$1"
    local health_url="$2"
    local health_type="$3"
    local elapsed=0

    if [[ "$SKIP_HEALTH" == "true" ]]; then
        log_dim "Health check skipped for ${container}"
        return 0
    fi

    while [[ $elapsed -lt $HEALTH_TIMEOUT ]]; do
        if check_health "$container" "$health_url" "$health_type"; then
            return 0
        fi
        sleep "$HEALTH_INTERVAL"
        elapsed=$((elapsed + HEALTH_INTERVAL))
        printf "." >&2
    done

    echo "" >&2
    return 1
}

# ══════════════════════════════════════════════════════════════════════════════
# CORE OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

ensure_network() {
    if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
        log_info "Creating Docker network: ${NETWORK_NAME}"
        docker network create "$NETWORK_NAME" >/dev/null 2>&1
        log_success "Network ${NETWORK_NAME} created"
    else
        log_dim "Network ${NETWORK_NAME} exists"
    fi
}

get_tier_services() {
    local tier_num="$1"
    local -n tier_ref="TIER_${tier_num}"
    echo "${tier_ref[@]}"
}

get_tier_name() {
    local tier_num="$1"
    local var="TIER_${tier_num}_NAME"
    echo "${!var}"
}

compose_up() {
    local compose_file="$1"
    local full_path="${COMPOSE_DIR}/${compose_file}"

    if [[ ! -f "$full_path" ]]; then
        log_warn "Compose file not found: ${compose_file}"
        return 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dim "[DRY RUN] Would start: ${compose_file}"
        return 0
    fi

    $DOCKER_COMPOSE -f "$full_path" up -d --remove-orphans 2>>"$BOOT_LOG"
}

compose_down() {
    local compose_file="$1"
    local full_path="${COMPOSE_DIR}/${compose_file}"

    if [[ ! -f "$full_path" ]]; then
        return 0
    fi

    $DOCKER_COMPOSE -f "$full_path" down --timeout 30 2>>"$BOOT_LOG"
}

boot_tier() {
    local tier_num="$1"
    local tier_name
    tier_name=$(get_tier_name "$tier_num")

    log_tier "${tier_num}: ${tier_name}"

    local -n services="TIER_${tier_num}"
    local total=${#services[@]}
    local started=0
    local failed=0

    for entry in "${services[@]}"; do
        IFS=':' read -r compose_file service_name container_name health_url health_type <<< "$entry"

        log_info "Starting ${service_name} (${container_name})..."

        # Start the service
        if compose_up "$compose_file"; then
            # Wait for health
            if wait_for_health "$container_name" "$health_url" "$health_type"; then
                log_success "${service_name} ✓ healthy"
                started=$((started + 1))
            else
                log_error "${service_name} ✗ health check timeout (${HEALTH_TIMEOUT}s)"
                failed=$((failed + 1))
            fi
        else
            log_error "${service_name} ✗ failed to start"
            failed=$((failed + 1))
        fi
    done

    echo "" | tee -a "$BOOT_LOG"
    if [[ $failed -eq 0 ]]; then
        log_success "Tier ${tier_num} complete: ${started}/${total} services healthy"
    else
        log_warn "Tier ${tier_num}: ${started}/${total} healthy, ${failed} failed"
    fi

    return $failed
}

shutdown_tier() {
    local tier_num="$1"
    local tier_name
    tier_name=$(get_tier_name "$tier_num")

    log_tier "${tier_num}: Stopping ${tier_name}"

    local -n services="TIER_${tier_num}"

    # Shutdown in reverse order
    local reversed=()
    for entry in "${services[@]}"; do
        reversed=("$entry" "${reversed[@]}")
    done

    for entry in "${reversed[@]}"; do
        IFS=':' read -r compose_file service_name container_name _ _ <<< "$entry"
        log_info "Stopping ${service_name}..."
        compose_down "$compose_file" && \
            log_success "${service_name} stopped" || \
            log_warn "${service_name} stop may have failed"
    done
}

show_status() {
    echo -e "\n${BOLD}${CYAN}  ⚛  OMNI QUANTUM ELITE — Platform Status${NC}"
    echo -e "  ${DIM}$(date '+%Y-%m-%d %H:%M:%S %Z')${NC}\n"

    for tier_num in "${ALL_TIERS[@]}"; do
        local tier_name
        tier_name=$(get_tier_name "$tier_num")
        echo -e "${BOLD}${MAGENTA}  Tier ${tier_num}: ${tier_name}${NC}"

        local -n services="TIER_${tier_num}"
        for entry in "${services[@]}"; do
            IFS=':' read -r _ service_name container_name health_url health_type <<< "$entry"

            # Check container state
            local state
            state=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null || echo "not found")

            local health_status=""
            if [[ "$state" == "running" ]]; then
                if check_health "$container_name" "$health_url" "$health_type" 2>/dev/null; then
                    health_status="${GREEN}● healthy${NC}"
                else
                    health_status="${YELLOW}◐ unhealthy${NC}"
                fi
            elif [[ "$state" == "not found" ]]; then
                health_status="${DIM}○ not running${NC}"
            else
                health_status="${RED}✗ ${state}${NC}"
            fi

            # Get uptime
            local uptime=""
            if [[ "$state" == "running" ]]; then
                uptime=$(docker inspect --format='{{.State.StartedAt}}' "$container_name" 2>/dev/null || echo "")
                if [[ -n "$uptime" ]]; then
                    local started_epoch
                    started_epoch=$(date -d "$uptime" +%s 2>/dev/null || echo "0")
                    local now_epoch
                    now_epoch=$(date +%s)
                    local diff=$((now_epoch - started_epoch))
                    if [[ $diff -gt 86400 ]]; then
                        uptime="${DIM}($(( diff / 86400 ))d)${NC}"
                    elif [[ $diff -gt 3600 ]]; then
                        uptime="${DIM}($(( diff / 3600 ))h)${NC}"
                    else
                        uptime="${DIM}($(( diff / 60 ))m)${NC}"
                    fi
                fi
            fi

            printf "    %-25s %b %s\n" "$service_name" "$health_status" "$uptime"
        done
        echo ""
    done

    # Summary counts
    local running=0 total=0 healthy=0
    for tier_num in "${ALL_TIERS[@]}"; do
        local -n services="TIER_${tier_num}"
        for entry in "${services[@]}"; do
            IFS=':' read -r _ _ container_name health_url health_type <<< "$entry"
            total=$((total + 1))
            local state
            state=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null || echo "not found")
            if [[ "$state" == "running" ]]; then
                running=$((running + 1))
                if check_health "$container_name" "$health_url" "$health_type" 2>/dev/null; then
                    healthy=$((healthy + 1))
                fi
            fi
        done
    done

    echo -e "  ${BOLD}Summary: ${GREEN}${healthy}${NC}${BOLD} healthy / ${YELLOW}${running}${NC}${BOLD} running / ${total} total${NC}\n"
}

restart_service() {
    local target="$1"
    local found=false

    for tier_num in "${ALL_TIERS[@]}"; do
        local -n services="TIER_${tier_num}"
        for entry in "${services[@]}"; do
            IFS=':' read -r compose_file service_name container_name health_url health_type <<< "$entry"
            if [[ "$service_name" == "$target" ]] || [[ "$container_name" == "$target" ]]; then
                found=true
                log_info "Restarting ${service_name}..."
                compose_down "$compose_file"
                sleep 2
                compose_up "$compose_file"
                if wait_for_health "$container_name" "$health_url" "$health_type"; then
                    log_success "${service_name} restarted and healthy"
                else
                    log_error "${service_name} restarted but health check failed"
                fi
                return 0
            fi
        done
    done

    if [[ "$found" == "false" ]]; then
        log_error "Service '${target}' not found in any tier"
        log_info "Available services:"
        for tier_num in "${ALL_TIERS[@]}"; do
            local -n services="TIER_${tier_num}"
            for entry in "${services[@]}"; do
                IFS=':' read -r _ service_name _ _ _ <<< "$entry"
                echo "  - ${service_name}"
            done
        done
        return 1
    fi
}

parse_tier_range() {
    local range="$1"
    local start_tier end_tier

    if [[ "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
        start_tier="${BASH_REMATCH[1]}"
        end_tier="${BASH_REMATCH[2]}"
    elif [[ "$range" =~ ^([0-9]+)$ ]]; then
        start_tier="${BASH_REMATCH[1]}"
        end_tier="${BASH_REMATCH[1]}"
    else
        log_error "Invalid tier range: ${range} (use: 0-6 or single tier number)"
        exit 1
    fi

    seq "$start_tier" "$end_tier"
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

BOOT_START=$(date +%s)

echo -e "${BOLD}${CYAN}"
echo "  ⚛  OMNI QUANTUM ELITE — Platform Boot Orchestrator"
echo "  ─────────────────────────────────────────────────────"
echo -e "${NC}"

case "$MODE" in
    status)
        show_status
        exit 0
        ;;

    shutdown)
        log_info "Initiating graceful shutdown (reverse tier order)..."
        for tier_num in 6 5 4 3 2 1 0; do
            shutdown_tier "$tier_num"
        done
        echo ""
        log_success "Platform shutdown complete"
        exit 0
        ;;

    restart)
        restart_service "$RESTART_SVC"
        exit $?
        ;;

    boot)
        # Determine which tiers to boot
        local tiers_to_boot
        if [[ -n "$TIER_RANGE" ]]; then
            tiers_to_boot=($(parse_tier_range "$TIER_RANGE"))
        else
            tiers_to_boot=("${ALL_TIERS[@]}")
        fi

        # Ensure network exists
        ensure_network

        # Boot each tier
        total_failed=0
        for tier_num in "${tiers_to_boot[@]}"; do
            boot_tier "$tier_num" || total_failed=$((total_failed + $?))

            # Gate: Don't proceed to next tier if current tier has critical failures
            # (tier 0 and 1 failures are blocking)
            if [[ $tier_num -le 1 ]] && [[ $total_failed -gt 0 ]]; then
                log_error "CRITICAL: Tier ${tier_num} has failures — aborting boot"
                log_error "Fix the above failures and re-run"
                exit 1
            fi
        done

        BOOT_END=$(date +%s)
        BOOT_DURATION=$((BOOT_END - BOOT_START))

        echo ""
        echo -e "${BOLD}${CYAN}  ═══════════════════════════════════════════════════${NC}"
        if [[ $total_failed -eq 0 ]]; then
            echo -e "${BOLD}${GREEN}  ⚛  Platform boot complete! (${BOOT_DURATION}s)${NC}"
        else
            echo -e "${BOLD}${YELLOW}  ⚛  Platform boot complete with warnings (${BOOT_DURATION}s)${NC}"
            echo -e "${YELLOW}      ${total_failed} service(s) had issues${NC}"
        fi
        echo -e "${BOLD}${CYAN}  ═══════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${DIM}Dashboard: http://${DOMAIN}:9500${NC}"
        echo -e "  ${DIM}Grafana:   http://${DOMAIN}:3000${NC}"
        echo -e "  ${DIM}Logs:      ${BOOT_LOG}${NC}"
        echo ""

        # Send notification via Mattermost if available
        if command -v curl &>/dev/null && [[ -n "${MATTERMOST_WEBHOOK_URL:-}" ]]; then
            curl -sf -X POST -H 'Content-Type: application/json' \
                -d "{\"text\":\"⚛ **Omni Quantum Elite** platform boot complete in ${BOOT_DURATION}s. ${total_failed} failures.\"}" \
                "$MATTERMOST_WEBHOOK_URL" >/dev/null 2>&1 || true
        fi

        exit $total_failed
        ;;
esac
