#!/usr/bin/env bash
set -Eeuo pipefail
URL="${UNLEASH_URL:-http://omni-unleash:4242}"
TOKEN="${UNLEASH_ADMIN_TOKEN:-{{ vault://secret/data/unleash#admin_token }}}"

for _ in $(seq 1 60); do
  curl -fsS "$URL/health" >/dev/null && break
  sleep 2
done
curl -fsS "$URL/health" >/dev/null

api(){ curl -fsS -H "Authorization: $TOKEN" -H 'Content-Type: application/json' "$@"; }
for env in development staging production; do api -X POST "$URL/api/admin/environments" -d "{\"name\":\"$env\"}" || true; done

for flag in pipeline.mutation-testing pipeline.ai-review-threshold pipeline.parallel-agents knowledge.auto-reingest knowledge.arxiv-monitor deploy.auto-staging deploy.blue-green billing.auto-invoice ui.new-dashboard; do
  api -X POST "$URL/api/admin/projects/default/features" -d "{\"name\":\"$flag\"}" || true
done

curl -fsS -X POST "http://omni-n8n:5678/webhook/unleash-init" -H 'Content-Type: application/json' -d '{"service":"unleash","event":"flags-configured","idempotent":true}' || true
curl -fsS "$URL/internal-backstage/prometheus" >/dev/null || true
