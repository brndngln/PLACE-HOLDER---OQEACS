#!/usr/bin/env bash
set -Eeuo pipefail
URL="${MEILI_URL:-http://omni-meilisearch:7700}"
KEY="${MEILI_KEY:-{{ vault://secret/data/meilisearch#admin_key }}}"

for _ in $(seq 1 60); do
  curl -fsS "$URL/health" >/dev/null && break
  sleep 2
done
curl -fsS "$URL/health" >/dev/null

api(){ curl -fsS -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' "$@"; }
for idx in knowledge-articles code-repositories project-issues platform-docs design-patterns; do
  api -X POST "$URL/indexes" -d "{\"uid\":\"$idx\",\"primaryKey\":\"id\"}" || true
done
api -X PATCH "$URL/indexes/knowledge-articles/settings/synonyms" -d '{"db":["database"],"k8s":["kubernetes"],"py":["python"]}' || true

curl -fsS -X POST "http://omni-n8n:5678/webhook/meilisearch-init" -H 'Content-Type: application/json' -d '{"service":"meilisearch","event":"indexes-ready","idempotent":true}' || true
curl -fsS -X POST "http://omni-mattermost-webhook:8066/hooks/omni-alerts" -H 'Content-Type: application/json' -d '{"text":"[omni-meilisearch] hardened init complete"}' || true
