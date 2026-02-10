#!/usr/bin/env bash
set -Eeuo pipefail
URL="${PLAUSIBLE_URL:-http://omni-plausible:8000}"
TOKEN="${PLAUSIBLE_API_KEY:-{{ vault://secret/data/plausible#api_key }}}"

for _ in $(seq 1 60); do
  curl -fsS "$URL/api/health" >/dev/null && break
  sleep 2
done
curl -fsS "$URL/api/health" >/dev/null

api() { curl -fsS -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' "$@"; }
existing="$(api "$URL/api/v1/sites" || true)"
for site in portal.omni.local docs.omni.local orchestrator.omni.local; do
  if ! echo "$existing" | grep -q "$site"; then
    api -X POST "$URL/api/v1/sites" -d "{\"domain\":\"$site\"}" || true
  fi
done

curl -fsS -X POST "http://omni-n8n:5678/webhook/plausible-init" -H 'Content-Type: application/json' -d '{"service":"plausible","event":"sites-configured","idempotent":true}' || true
curl -fsS -X POST "http://omni-mattermost-webhook:8066/hooks/omni-general" -H 'Content-Type: application/json' -d '{"text":"[omni-plausible] hardening init complete"}' || true
curl -fsS "$URL/metrics" >/dev/null || true
