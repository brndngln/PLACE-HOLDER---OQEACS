#!/usr/bin/env bash
set -Eeuo pipefail

LISTMONK_URL="${LISTMONK_URL:-http://omni-listmonk:9000}"
LISTMONK_USER="${LISTMONK_ADMIN_USER:-{{ vault://secret/data/listmonk#admin_username }}}"
LISTMONK_PASS="${LISTMONK_ADMIN_PASS:-{{ vault://secret/data/listmonk#admin_password }}}"
MM_WEBHOOK="${MM_WEBHOOK:-http://omni-mattermost-webhook:8066/hooks/omni-alerts}"
N8N_WEBHOOK="${N8N_WEBHOOK:-http://omni-n8n:5678/webhook/listmonk-events}"

log() { printf '[listmonk-init] %s\n' "$*"; }
api() { curl -fsS -H "Authorization: Basic $AUTH" -H "Content-Type: application/json" "$@"; }
ensure_list() {
  local name="$1" type="$2" description="$3"
  if curl -fsS "$LISTMONK_URL/api/lists" -H "Authorization: Basic $AUTH" | grep -q "\"name\":\"$name\""; then
    log "list exists: $name"
  else
    api -X POST "$LISTMONK_URL/api/lists" -d "{\"name\":\"$name\",\"type\":\"$type\",\"description\":\"$description\"}"
    log "list created: $name"
  fi
}

for _ in $(seq 1 60); do
  curl -fsS "$LISTMONK_URL/api/health" >/dev/null && break
  sleep 2
done
curl -fsS "$LISTMONK_URL/api/health" >/dev/null

listmonk --install --yes || true
AUTH="$(printf "%s:%s" "$LISTMONK_USER" "$LISTMONK_PASS" | base64 -w0)"

ensure_list transactional private "invoices,resets,confirmations,alerts"
ensure_list updates public "client announcements"
ensure_list internal private "team notifications"

api -X POST "$LISTMONK_URL/api/settings" -d "{\"auth\":{\"provider\":\"oidc\",\"issuer\":\"{{ vault://secret/data/authentik/oidc#issuer }}\",\"client_id\":\"{{ vault://secret/data/authentik/oidc#client_id }}\",\"client_secret\":\"{{ vault://secret/data/authentik/oidc#client_secret }}\"}}" || true
curl -fsS -X POST "$N8N_WEBHOOK" -H "Content-Type: application/json" -d '{"service":"listmonk","event":"init-complete","idempotent":true}' || true
curl -fsS -X POST "$MM_WEBHOOK" -H "Content-Type: application/json" -d '{"text":"[omni-listmonk] hardening init completed"}' || true
curl -fsS "$LISTMONK_URL/metrics" >/dev/null || true
