#!/usr/bin/env bash
set -Eeuo pipefail

PACT_URL="${PACT_URL:-http://omni-pact-broker:9292}"
PACT_USER="${PACT_USER:-${PACT_BROKER_BASIC_AUTH_USERNAME:-admin}}"
PACT_PASS="${PACT_PASS:-${PACT_BROKER_BASIC_AUTH_PASSWORD:-admin}}"
MM_WEBHOOK="${MM_WEBHOOK:-http://omni-mattermost-webhook:8066/hooks/builds}"

auth=(-u "${PACT_USER}:${PACT_PASS}")

for _ in $(seq 1 80); do
  curl -fsS "${PACT_URL}/diagnostic/status/heartbeat" >/dev/null && break
  sleep 2
done

api(){ curl -fsS "${auth[@]}" -H "Content-Type: application/json" "$@"; }

for p in omni-orchestrator omni-token-infinity omni-openhands-orchestrator omni-swe-agent-handler omni-knowledge-ingestor omni-freshness-monitor omni-webhook-router; do
  api -X PUT "${PACT_URL}/pacticipants/${p}" -d "{\"name\":\"${p}\"}" || true
done

api -X POST "${PACT_URL}/webhooks" -d '{"events":["contract_content_changed"],"request":{"method":"POST","url":"http://omni-woodpecker-server:8000/api/repos/omni/contract-verify/builds"}}' || true
api -X POST "${PACT_URL}/webhooks" -d "{\"events\":[\"contract_published\"],\"request\":{\"method\":\"POST\",\"url\":\"${MM_WEBHOOK}\",\"body\":\"{\\\"text\\\":\\\"Pact contract changed and verification needed\\\"}\"}}" || true
api -X POST "${PACT_URL}/webhooks" -d '{"events":["provider_verification_published"],"request":{"method":"POST","url":"http://omni-n8n:5678/webhook/plane-ticket"}}' || true

curl -fsS -X POST "${MM_WEBHOOK}" -H "Content-Type: application/json" -d '{"text":"[omni-pact-broker] init complete with pacticipants and webhooks"}' || true
