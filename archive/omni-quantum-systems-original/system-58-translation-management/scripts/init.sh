#!/usr/bin/env bash
set -Eeuo pipefail
URL="${TOLGEE_URL:-http://omni-tolgee:8080}"
KEY="${TOLGEE_API_KEY:-{{ vault://secret/data/tolgee#admin_api_key }}}"

for _ in $(seq 1 60); do
  curl -fsS "$URL/actuator/health" >/dev/null && break
  sleep 2
done
curl -fsS "$URL/actuator/health" >/dev/null

api(){ curl -fsS -H "X-API-Key: $KEY" -H 'Content-Type: application/json' "$@"; }
for p in client-apps platform-ui email-templates; do api -X POST "$URL/v2/projects" -d "{\"name\":\"$p\"}" || true; done
for lang in es fr de ja zh pt ko; do api -X POST "$URL/v2/projects/1/languages" -d "{\"tag\":\"$lang\"}" || true; done

curl -fsS -X POST "http://omni-n8n:5678/webhook/tolgee-updates" -H 'Content-Type: application/json' -d '{"service":"tolgee","event":"translation_update","idempotent":true}' || true
curl -fsS -X POST "http://omni-mattermost-webhook:8066/hooks/omni-general" -H 'Content-Type: application/json' -d '{"text":"[omni-tolgee] hardened init complete"}' || true
