#!/usr/bin/env bash
set -euo pipefail

API_BASE="http://omni-crater:80/api/v1"
TOKEN="${CRATER_API_TOKEN}"
N8N_BASE="http://omni-n8n:5678/webhook"
MM_WEBHOOK="http://omni-mattermost-webhook:8066"

OIDC_CLIENT_ID=$(vault kv get -field=client_id secret/authentik/crater)
OIDC_CLIENT_SECRET=$(vault kv get -field=client_secret secret/authentik/crater)
BANK_NAME=$(vault kv get -field=bank_name secret/crater/bank)
BANK_ACCOUNT=$(vault kv get -field=account_number secret/crater/bank)
BANK_ROUTING=$(vault kv get -field=routing_number secret/crater/bank)
BANK_SWIFT=$(vault kv get -field=swift_code secret/crater/bank)

until curl -sf http://omni-crater:80/health; do sleep 3; done

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
    \"oidc_discovery_url\": \"http://omni-authentik:9000/application/o/crater/.well-known/openid-configuration\"
  }"

# Company profile
curl -s -X PATCH "${API_BASE}/company" -H "${auth_header}" -H "${ct}" \
  -d '{
    "name": "Omni Quantum Elite",
    "address_street_1": "123 Quantum Drive",
    "city": "Tech City",
    "state": "CA",
    "zip": "94000",
    "country_id": 231,
    "phone": "+1-555-QUANTUM",
    "email": "billing@omni-quantum.local"
  }'

# Tax settings
curl -s -X POST "${API_BASE}/tax-types" -H "${auth_header}" -H "${ct}" \
  -d '{"name": "Standard Tax", "percent": 0, "compound_tax": false, "collective_tax": false, "description": "No tax - varies by jurisdiction"}'

# Auto-numbering: INV-{YEAR}-{SEQ:4}
curl -s -X PATCH "${API_BASE}/settings" -H "${auth_header}" -H "${ct}" \
  -d '{
    "invoice_prefix": "INV-",
    "invoice_auto_generate": true,
    "invoice_number_format": "{PREFIX}{YEAR}-{SEQUENCE:4}",
    "fiscal_year": "1-12"
  }'

# Payment methods: bank transfer
curl -s -X POST "${API_BASE}/payment-methods" -H "${auth_header}" -H "${ct}" \
  -d "{
    \"name\": \"Bank Transfer\",
    \"driver\": \"bank_transfer\",
    \"settings\": {
      \"bank_name\": \"${BANK_NAME}\",
      \"account_number\": \"${BANK_ACCOUNT}\",
      \"routing_number\": \"${BANK_ROUTING}\",
      \"swift_code\": \"${BANK_SWIFT}\"
    }
  }"

# Payment methods: Stripe via Nango
curl -s -X POST "${API_BASE}/payment-methods" -H "${auth_header}" -H "${ct}" \
  -d '{
    "name": "Stripe",
    "driver": "stripe",
    "settings": {
      "proxy_url": "http://omni-nango:3003/proxy/stripe",
      "connection_id": "stripe-main"
    }
  }'

# Email via Listmonk SMTP
curl -s -X PATCH "${API_BASE}/settings" -H "${auth_header}" -H "${ct}" \
  -d '{
    "mail_driver": "smtp",
    "mail_host": "omni-listmonk",
    "mail_port": 25,
    "mail_from_address": "invoices@omni-quantum.local",
    "mail_from_name": "Omni Quantum Billing"
  }'

# Template: standard-project
curl -s -X POST "${API_BASE}/invoice-templates" -H "${auth_header}" -H "${ct}" \
  -d "{
    \"name\": \"standard-project\",
    \"payment_terms\": \"net_30\",
    \"notes\": \"Payment due within 30 days.\\n\\nBank Transfer Details:\\nBank: ${BANK_NAME}\\nAccount: ${BANK_ACCOUNT}\\nRouting: ${BANK_ROUTING}\\nSWIFT: ${BANK_SWIFT}\",
    \"line_item_format\": \"itemized\"
  }"

# Template: hourly-rate
curl -s -X POST "${API_BASE}/invoice-templates" -H "${auth_header}" -H "${ct}" \
  -d '{
    "name": "hourly-rate",
    "payment_terms": "net_15",
    "notes": "Payment due within 15 days. Timesheet attached.",
    "line_item_format": "hours_x_rate",
    "attach_timesheet": true
  }'

# Template: milestone
curl -s -X POST "${API_BASE}/invoice-templates" -H "${auth_header}" -H "${ct}" \
  -d '{
    "name": "milestone",
    "payment_terms": "net_30",
    "notes": "Milestone-based billing. Payment due within 30 days of milestone completion.",
    "line_item_format": "milestone_percentage",
    "link_to_plane": true
  }'

# Webhooks
create_webhook "invoice.sent" "${N8N_BASE}/invoice-sent"
create_webhook "invoice.paid" "${N8N_BASE}/invoice-paid"
create_webhook "invoice.overdue" "${N8N_BASE}/invoice-overdue"

notify_mm "#financial" "Crater initialized: company profile, 3 invoice templates, payment methods (bank + Stripe), auto-numbering INV-YYYY-NNNN."
echo "Crater init complete."
