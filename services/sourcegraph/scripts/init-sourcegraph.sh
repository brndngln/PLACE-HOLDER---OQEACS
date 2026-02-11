#!/usr/bin/env bash
#
# Initialize Sourcegraph with Gitea repositories
#
# This script waits for the Sourcegraph instance to become ready and then
# configures an external service to pull all repositories from the Gitea
# server. It requires the following environment variables:
#   SOURCEGRAPH_URL  – base URL of Sourcegraph (default http://omni-sourcegraph:7080)
#   SOURCEGRAPH_TOKEN – admin access token for Sourcegraph API
#   GITEA_URL        – base URL of Gitea (default http://omni-gitea:3000)
#   GITEA_TOKEN      – API token with read permissions on Gitea repos

set -euo pipefail

COLOR_YELLOW="\033[33m"
COLOR_GREEN="\033[32m"
COLOR_RESET="\033[0m"

log() {
  echo -e "${COLOR_GREEN}[INIT] $*${COLOR_RESET}"
}

warn() {
  echo -e "${COLOR_YELLOW}[WARN] $*${COLOR_RESET}" >&2
}

SOURCEGRAPH_URL=${SOURCEGRAPH_URL:-http://omni-sourcegraph:7080}
GITEA_URL=${GITEA_URL:-http://omni-gitea:3000}
if [[ -z "${SOURCEGRAPH_TOKEN:-}" || -z "${GITEA_TOKEN:-}" ]]; then
  warn "SOURCEGRAPH_TOKEN and GITEA_TOKEN environment variables must be set"
  exit 1
fi

log "Waiting for Sourcegraph to become healthy at $SOURCEGRAPH_URL"
for i in {1..30}; do
  if curl -s -f "$SOURCEGRAPH_URL/healthz" >/dev/null; then
    log "Sourcegraph is healthy"
    break
  fi
  sleep 5
  if [[ "$i" -eq 30 ]]; then
    warn "Sourcegraph did not become healthy in time"
    exit 1
  fi
done

log "Creating Gitea external service"
payload=$(cat <<JSON
{
  "kind": "GITEA",
  "displayName": "Omni Gitea",
  "config": "{\"url\":\"$GITEA_URL\", \"token\":\"$GITEA_TOKEN\", \"username\":\"\", \"repositoryQuery\":[\"^.*\"]}"
}
JSON
)

response=$(curl -s -w "%{http_code}" -o /tmp/sg-response.out \
  -X POST "$SOURCEGRAPH_URL/.api/external-services" \
  -H "Content-Type: application/json" \
  -H "Authorization: token $SOURCEGRAPH_TOKEN" \
  --data "$payload")

http_code="${response:(-3)}"
if [[ "$http_code" == "201" || "$http_code" == "200" ]]; then
  log "External service configured successfully"
else
  warn "Failed to configure external service (HTTP $http_code)"
  cat /tmp/sg-response.out
  exit 1
fi