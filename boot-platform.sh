#!/bin/bash
#
# boot-platform.sh
#
# Tiered boot orchestrator for the Omni platform. This script
# bootstraps the entire stack of services in a deterministic order,
# performing health checks between tiers to ensure dependencies are
# fully operational before higher-level systems start. Services are
# grouped into tiers as defined below. Each tier is started with
# `docker compose` if a compose file exists for the service. After
# starting, the script polls Docker health status for each container
# up to 30 times with a 2‑second interval. Failure to achieve a
# healthy state results in immediate termination of the boot process.
#
# Usage:
#   bash scripts/boot-platform.sh
#
# Requirements:
#   - Docker and docker-compose (v2) installed
#   - A `.env` file in the project root containing required secrets
#   - Service directories located under `systems/` with a
#     `docker-compose.yml` file for each service

set -euo pipefail

#############################
# COLOR LOGGING FUNCTIONS   #
#############################
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
RESET="\033[0m"

log_info()    { printf "%b[INFO ]%b %s\n"   "$BLUE" "$RESET" "$1"; }
log_success() { printf "%b[OK   ]%b %s\n"   "$GREEN" "$RESET" "$1"; }
log_warn()    { printf "%b[WARN ]%b %s\n"  "$YELLOW" "$RESET" "$1"; }
log_error()   { printf "%b[ERROR]%b %s\n" "$RED" "$RESET" "$1"; }

#############################
# NETWORK SETUP             #
#############################

NETWORK_NAME="omni-quantum-network"

# Ensure the Docker network exists
ensure_network() {
  if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    log_info "Creating Docker network $NETWORK_NAME"
    docker network create "$NETWORK_NAME" >/dev/null
    log_success "Network $NETWORK_NAME created"
  else
    log_info "Docker network $NETWORK_NAME already exists"
  fi
}

#############################
# HEALTH CHECK              #
#############################

# Check the health status of a container. Retries up to max_retries
# times waiting delay seconds between attempts. Status symbols:
# 🟢 – healthy
# 🟡 – degraded (not healthy but still running)
# 🔴 – failed (did not become healthy)
check_container_health() {
  local container_name="$1"
  local max_retries=30
  local delay=2
  local attempt=0
  local status
  while true; do
    # Query container health via docker inspect
    status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}nohealth{{end}}' "$container_name" 2>/dev/null || echo 'missing')
    if [[ "$status" == "healthy" ]]; then
      if (( attempt == 0 )); then
        printf "🟢 %s is healthy\n" "$container_name"
      else
        printf "🟡 %s recovered to healthy state after %d retries\n" "$container_name" "$attempt"
      fi
      return 0
    elif [[ "$status" == "nohealth" ]]; then
      printf "🟢 %s has no health check configured (assuming healthy)\n" "$container_name"
      return 0
    elif [[ "$status" == "missing" ]]; then
      printf "🔴 %s container not found\n" "$container_name"
      return 1
    fi
    # Not healthy yet
    if (( attempt >= max_retries )); then
      printf "🔴 %s failed to become healthy (status: %s)\n" "$container_name" "$status"
      return 1
    fi
    attempt=$((attempt+1))
    sleep "$delay"
  done
}

#############################
# SERVICE STARTUP           #
#############################

# Start a service using docker compose if its compose file exists.
# Arguments: service directory name (relative to systems/)
start_service() {
  local svc_dir="$1"
  local compose_file="systems/${svc_dir}/docker-compose.yml"
  if [[ -f "$compose_file" ]]; then
    log_info "Starting service ${svc_dir} via docker compose"
    docker compose --env-file .env -f "$compose_file" up -d --remove-orphans
  else
    log_warn "Compose file not found for $svc_dir (skipping startup)"
  fi
}

# Boot a list of services constituting a tier. Accepts the tier name
# for logging and an array of service identifiers. Each identifier
# corresponds both to a directory under systems/ and a container name.
boot_tier() {
  local tier_name="$1"
  shift
  local services=("$@")
  log_info "—— Booting Tier ${tier_name} — ${#services[@]} service(s)"
  for svc in "${services[@]}"; do
    start_service "$svc"
  done
  # Health gate
  local failures=0
  for svc in "${services[@]}"; do
    # Container name equals svc by convention
    if ! check_container_health "$svc"; then
      failures=$((failures+1))
    fi
  done
  if (( failures > 0 )); then
    log_error "Tier ${tier_name} boot failed: ${failures} service(s) unhealthy"
    exit 1
  else
    log_success "Tier ${tier_name} boot complete"
  fi
}

#############################
# TIER DEFINITIONS          #
#############################

# Define services by tier. The names must correspond both to the
# docker-compose directory under systems/ and the container name.
TIER_0=(
  omni-postgres
  omni-redis
  omni-minio
)
TIER_1=(
  omni-vault
  omni-traefik
  omni-authentik
  omni-prometheus
  omni-loki
  omni-grafana
)
TIER_2=(
  omni-ollama
  omni-litellm
  omni-gitea
  omni-mattermost
  omni-qdrant
  omni-langfuse
)
TIER_3=(
  omni-n8n
  omni-plane
  omni-nango
  omni-flowise
  omni-wikijs
  omni-superset
  omni-calcom
)
TIER_4=(
  omni-openhands
  omni-swe-agent
  omni-token-infinity
  omni-omi-bridge
)
TIER_5=(
  omni-pulse-command-pro
  omni-log-nexus-pro
  omni-guardian-eye
  omni-backup-fortress-pro
  omni-cryptographic-fortress-pro
  omni-gateway-sentinel-pro
  omni-build-forge
  omni-code-forge
)
TIER_6=(
  omni-omni-command
)

#############################
# MAIN PROGRAM              #
#############################

main() {
  ensure_network
  boot_tier 0 "${TIER_0[@]}"
  boot_tier 1 "${TIER_1[@]}"
  boot_tier 2 "${TIER_2[@]}"
  boot_tier 3 "${TIER_3[@]}"
  boot_tier 4 "${TIER_4[@]}"
  boot_tier 5 "${TIER_5[@]}"
  boot_tier 6 "${TIER_6[@]}"
  log_success "All tiers booted successfully"
}

main "$@"