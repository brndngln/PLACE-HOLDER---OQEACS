#!/usr/bin/env bash
set -Eeuo pipefail
CW_URL="${CHATWOOT_URL:-http://omni-chatwoot:3000}"
TOKEN="${CHATWOOT_PLATFORM_TOKEN:-{{ vault://secret/data/chatwoot#platform_api_token }}}"
MM_WEBHOOK="${MM_WEBHOOK:-http://omni-mattermost-webhook:8066/hooks/omni-general}"
N8N_WEBHOOK="${N8N_WEBHOOK:-http://omni-n8n:5678/webhook/chatwoot-events}"
api() { curl -fsS -H "api_access_token: $TOKEN" -H "Content-Type: application/json" "$@"; }

for _ in $(seq 1 90); do
  curl -fsS "$CW_URL" >/dev/null && break
  sleep 2
done
curl -fsS "$CW_URL" >/dev/null

# Idempotent inbox creation by name check.
existing="$(api "$CW_URL/api/v1/accounts/1/inboxes" || true)"
if ! echo "$existing" | grep -q 'Website Live Chat'; then
  api -X POST "$CW_URL/api/v1/accounts/1/inboxes" -d '{"name":"Website Live Chat","channel":{"type":"web_widget"}}' || true
fi
if ! echo "$existing" | grep -q 'Email Support'; then
  api -X POST "$CW_URL/api/v1/accounts/1/inboxes" -d '{"name":"Email Support","channel":{"type":"email","email":"support@omni.local"}}' || true
fi
if ! echo "$existing" | grep -q 'API Inbox'; then
  api -X POST "$CW_URL/api/v1/accounts/1/inboxes" -d '{"name":"API Inbox","channel":{"type":"api"}}' || true
fi

api -X POST "$CW_URL/api/v1/accounts/1/automation_rules" -d '{"name":"financial-routing","event_name":"message_created","conditions":[{"attribute_key":"content","query_operator":"contains","values":["invoice","payment"]}],"actions":[{"action_name":"add_label","action_params":["financial"]}]}' || true
api -X POST "$CW_URL/api/v1/accounts/1/automation_rules" -d '{"name":"technical-routing","event_name":"message_created","conditions":[{"attribute_key":"content","query_operator":"contains","values":["bug","error","broken"]}],"actions":[{"action_name":"add_label","action_params":["technical"]}]}' || true

curl -fsS -X POST "$N8N_WEBHOOK" -H "Content-Type: application/json" -d '{"service":"chatwoot","event":"bootstrap","webhooks":["new_conversation","sla_breach"],"idempotent":true}' || true
curl -fsS -X POST "$MM_WEBHOOK" -H "Content-Type: application/json" -d '{"text":"[omni-chatwoot] support center hardened init complete"}' || true
