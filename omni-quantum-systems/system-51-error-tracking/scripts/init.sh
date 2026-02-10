#!/usr/bin/env bash
set -Eeuo pipefail
URL="${GLITCHTIP_URL:-http://omni-glitchtip:8000}"
TOKEN="${GLITCHTIP_API_TOKEN:-{{ vault://secret/data/glitchtip#api_token }}}"

for _ in $(seq 1 90); do
  curl -fsS "$URL/_health/" >/dev/null && break
  sleep 2
done
curl -fsS "$URL/_health/" >/dev/null

api(){ curl -fsS -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' "$@"; }
for p in omni-orchestrator omni-pipeline omni-agents omni-knowledge omni-financial omni-infrastructure omni-business; do
  api -X POST "$URL/api/0/teams/omni/omni/projects/" -d "{\"slug\":\"$p\",\"name\":\"$p\"}" || true
done

curl -fsS -X POST "http://omni-n8n:5678/webhook/glitchtip-init" -H 'Content-Type: application/json' -d '{"service":"glitchtip","event":"projects-created","idempotent":true}' || true
curl -fsS -X POST "http://omni-mattermost-webhook:8066/hooks/omni-alerts" -H 'Content-Type: application/json' -d '{"text":"[omni-glitchtip] hardened init complete"}' || true
