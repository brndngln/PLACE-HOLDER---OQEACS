#!/usr/bin/env bash
set -euo pipefail

API_BASE="http://omni-plane-web:3000/api/v1"
TOKEN="${PLANE_API_TOKEN}"
N8N_BASE="http://omni-n8n:5678/webhook"
MM_WEBHOOK="http://omni-mattermost-webhook:8066"

OIDC_CLIENT_ID=$(vault kv get -field=client_id secret/authentik/plane)
OIDC_CLIENT_SECRET=$(vault kv get -field=client_secret secret/authentik/plane)

until curl -sf http://omni-plane-web:3000/health; do sleep 3; done

auth_header="Authorization: Bearer ${TOKEN}"
ct="Content-Type: application/json"

create_webhook() {
  curl -s -X POST "${API_BASE}/webhooks" -H "${auth_header}" -H "${ct}" \
    -d "{\"event\":\"$1\",\"url\":\"$2\"}"
}

notify_mm() {
  curl -s -X POST "${MM_WEBHOOK}" -H "${ct}" -d "{\"channel\":\"$1\",\"text\":\"$2\"}"
}

# Create workspace
WORKSPACE_SLUG="omni-quantum"
curl -s -X POST "${API_BASE}/workspaces/" -H "${auth_header}" -H "${ct}" \
  -d "{\"name\":\"Omni Quantum\",\"slug\":\"${WORKSPACE_SLUG}\"}"

WS="${API_BASE}/workspaces/${WORKSPACE_SLUG}"

# Configure Authentik SSO
curl -s -X PATCH "${WS}/settings/" -H "${auth_header}" -H "${ct}" \
  -d "{
    \"oidc_provider\": \"authentik\",
    \"oidc_client_id\": \"${OIDC_CLIENT_ID}\",
    \"oidc_client_secret\": \"${OIDC_CLIENT_SECRET}\",
    \"oidc_discovery_url\": \"http://omni-authentik:9000/application/o/plane/.well-known/openid-configuration\"
  }"

# --- Template 1: Client Project ---
CLIENT_PROJECT=$(curl -s -X POST "${WS}/projects/" -H "${auth_header}" -H "${ct}" \
  -d '{
    "name": "Client Project Template",
    "identifier": "CPT",
    "network": 2,
    "is_template": true
  }' | jq -r '.id')

CLIENT_STATES=("Backlog" "Specification" "In Development" "AI Review" "Testing" "Staging" "Production" "Complete")
for i in "${!CLIENT_STATES[@]}"; do
  curl -s -X POST "${WS}/projects/${CLIENT_PROJECT}/states/" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${CLIENT_STATES[$i]}\",\"sequence\":$((i * 1000)),\"group\":\"started\"}"
done

CLIENT_LABELS=("feature" "bug" "refactor" "optimization" "documentation" "infrastructure")
for label in "${CLIENT_LABELS[@]}"; do
  curl -s -X POST "${WS}/projects/${CLIENT_PROJECT}/labels/" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${label}\"}"
done

PRIORITIES=("Urgent" "High" "Medium" "Low")
for i in "${!PRIORITIES[@]}"; do
  curl -s -X POST "${WS}/projects/${CLIENT_PROJECT}/priorities/" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${PRIORITIES[$i]}\",\"sequence\":$i}"
done

CUSTOM_FIELDS='[
  {"name":"client_name","type":"text"},
  {"name":"budget","type":"number"},
  {"name":"deadline","type":"date"},
  {"name":"quality_score","type":"number"}
]'
echo "${CUSTOM_FIELDS}" | jq -c '.[]' | while read -r field; do
  curl -s -X POST "${WS}/projects/${CLIENT_PROJECT}/custom-fields/" -H "${auth_header}" -H "${ct}" -d "${field}"
done

MODULES=("Planning" "Sprint 1" "Sprint 2" "Sprint 3" "Polish" "Launch")
for mod in "${MODULES[@]}"; do
  curl -s -X POST "${WS}/projects/${CLIENT_PROJECT}/modules/" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${mod}\"}"
done

for view in "board" "list" "timeline"; do
  curl -s -X POST "${WS}/projects/${CLIENT_PROJECT}/views/" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${view}\",\"type\":\"${view}\"}"
done

# --- Template 2: Internal Infrastructure ---
INFRA_PROJECT=$(curl -s -X POST "${WS}/projects/" -H "${auth_header}" -H "${ct}" \
  -d '{
    "name": "Internal Infrastructure Template",
    "identifier": "IIT",
    "network": 2,
    "is_template": true
  }' | jq -r '.id')

INFRA_STATES=("Backlog" "Designing" "Building" "Testing" "Deployed" "Monitoring")
for i in "${!INFRA_STATES[@]}"; do
  curl -s -X POST "${WS}/projects/${INFRA_PROJECT}/states/" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${INFRA_STATES[$i]}\",\"sequence\":$((i * 1000)),\"group\":\"started\"}"
done

INFRA_LABELS=("critical" "high" "standard" "enhancement" "tech-debt")
for label in "${INFRA_LABELS[@]}"; do
  curl -s -X POST "${WS}/projects/${INFRA_PROJECT}/labels/" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${label}\"}"
done

# --- Template 3: Bug Fix Sprint ---
BUG_PROJECT=$(curl -s -X POST "${WS}/projects/" -H "${auth_header}" -H "${ct}" \
  -d '{
    "name": "Bug Fix Sprint Template",
    "identifier": "BFS",
    "network": 2,
    "is_template": true
  }' | jq -r '.id')

BUG_STATES=("Reported" "Reproducing" "Fixing" "Verifying" "Resolved")
for i in "${!BUG_STATES[@]}"; do
  curl -s -X POST "${WS}/projects/${BUG_PROJECT}/states/" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${BUG_STATES[$i]}\",\"sequence\":$((i * 1000)),\"group\":\"started\"}"
done

BUG_LABELS=("severity-critical" "severity-high" "severity-medium" "severity-low" "regression")
for label in "${BUG_LABELS[@]}"; do
  curl -s -X POST "${WS}/projects/${BUG_PROJECT}/labels/" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${label}\"}"
done

# --- Webhooks ---
create_webhook "issue.state_changed" "${N8N_BASE}/plane-issue-state-changed"
create_webhook "issue.created" "${N8N_BASE}/plane-issue-created"
create_webhook "issue.assigned" "${N8N_BASE}/plane-issue-assigned"

notify_mm "#general" "Plane initialized: workspace omni-quantum with 3 project templates configured."
echo "Plane init complete."
