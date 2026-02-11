#!/usr/bin/env bash
set -euo pipefail

API_BASE="https://notion.so"
TOKEN="${TWENTY_API_TOKEN}"
N8N_BASE="http://omni-n8n:5678/webhook"
MM_WEBHOOK="http://omni-mattermost-webhook:8066"

OIDC_CLIENT_ID=$(vault kv get -field=client_id secret/authentik/twenty)
OIDC_CLIENT_SECRET=$(vault kv get -field=client_secret secret/authentik/twenty)

until curl -sf https://notion.so/health; do sleep 3; done

auth_header="Authorization: Bearer ${TOKEN}"
ct="Content-Type: application/json"

create_webhook() {
  curl -s -X POST "${API_BASE}/webhooks" -H "${auth_header}" -H "${ct}" \
    -d "{\"event\":\"$1\",\"url\":\"$2\"}"
}

notify_mm() {
  curl -s -X POST "${MM_WEBHOOK}" -H "${ct}" -d "{\"channel\":\"$1\",\"text\":\"$2\"}"
}

# Configure Authentik SSO
curl -s -X PATCH "${API_BASE}/settings" -H "${auth_header}" -H "${ct}" \
  -d "{
    \"oidc_enabled\": true,
    \"oidc_client_id\": \"${OIDC_CLIENT_ID}\",
    \"oidc_client_secret\": \"${OIDC_CLIENT_SECRET}\",
    \"oidc_discovery_url\": \"http://omni-authentik:9000/application/o/twenty/.well-known/openid-configuration\"
  }"

# Pipeline stages
STAGES=("Lead" "Qualified" "Proposal Sent" "Negotiation" "Active Project" "Completed" "Lost")
for i in "${!STAGES[@]}"; do
  curl -s -X POST "${API_BASE}/pipeline-stages" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${STAGES[$i]}\",\"position\":$i,\"color\":\"#$(printf '%06x' $((RANDOM * RANDOM)))\"}"
done

# Custom fields: Companies
COMPANY_FIELDS=(
  '{"name":"industry","type":"TEXT","objectName":"company"}'
  '{"name":"company_size","type":"SELECT","objectName":"company","options":["startup","smb","mid-market","enterprise"]}'
  '{"name":"source","type":"SELECT","objectName":"company","options":["referral","website","cold","event"]}'
  '{"name":"annual_budget","type":"NUMBER","objectName":"company"}'
)
for field in "${COMPANY_FIELDS[@]}"; do
  curl -s -X POST "${API_BASE}/custom-fields" -H "${auth_header}" -H "${ct}" -d "${field}"
done

# Custom fields: Deals
DEAL_FIELDS=(
  '{"name":"project_type","type":"SELECT","objectName":"deal","options":["web-app","api","mobile","data-pipeline","ai-integration","full-platform"]}'
  '{"name":"estimated_hours","type":"NUMBER","objectName":"deal"}'
  '{"name":"hourly_rate","type":"NUMBER","objectName":"deal"}'
  '{"name":"total_value","type":"NUMBER","objectName":"deal","formula":"estimated_hours * hourly_rate"}'
  '{"name":"deadline","type":"DATE","objectName":"deal"}'
  '{"name":"quality_score","type":"NUMBER","objectName":"deal"}'
  '{"name":"plane_project_id","type":"TEXT","objectName":"deal"}'
  '{"name":"gitea_repo","type":"TEXT","objectName":"deal"}'
)
for field in "${DEAL_FIELDS[@]}"; do
  curl -s -X POST "${API_BASE}/custom-fields" -H "${auth_header}" -H "${ct}" -d "${field}"
done

# Custom fields: Contacts
CONTACT_FIELDS=(
  '{"name":"role","type":"TEXT","objectName":"contact"}'
  '{"name":"timezone","type":"TEXT","objectName":"contact"}'
  '{"name":"preferred_contact","type":"SELECT","objectName":"contact","options":["email","slack","phone"]}'
  '{"name":"last_meeting","type":"DATE","objectName":"contact"}'
)
for field in "${CONTACT_FIELDS[@]}"; do
  curl -s -X POST "${API_BASE}/custom-fields" -H "${auth_header}" -H "${ct}" -d "${field}"
done

# Webhooks
create_webhook "deal.stage_changed" "${N8N_BASE}/twenty-deal-stage-changed"
create_webhook "deal.created" "${N8N_BASE}/twenty-deal-created"

notify_mm "#general" "Twenty CRM initialized: pipeline stages, custom fields for Companies/Deals/Contacts, webhooks configured."
echo "Twenty CRM init complete."
