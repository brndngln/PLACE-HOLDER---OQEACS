#!/usr/bin/env bash
set -euo pipefail

API_BASE="http://omni-calcom:3000/api/v1"
TOKEN="${CALCOM_API_TOKEN}"
N8N_BASE="http://omni-n8n:5678/webhook"
MM_WEBHOOK="http://omni-mattermost-webhook:8066"

OIDC_CLIENT_ID=$(vault kv get -field=client_id secret/authentik/calcom)
OIDC_CLIENT_SECRET=$(vault kv get -field=client_secret secret/authentik/calcom)

until curl -sf http://omni-calcom:3000/health; do sleep 3; done

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
    \"oidc_client_id\": \"${OIDC_CLIENT_ID}\",
    \"oidc_client_secret\": \"${OIDC_CLIENT_SECRET}\",
    \"oidc_discovery_url\": \"http://omni-authentik:9000/application/o/calcom/.well-known/openid-configuration\"
  }"

# Configure timezone and business hours
curl -s -X PATCH "${API_BASE}/schedules/default" -H "${auth_header}" -H "${ct}" \
  -d '{
    "timeZone": "UTC",
    "availability": [
      {"days": [1,2,3,4,5], "startTime": "09:00", "endTime": "17:00"}
    ]
  }'

# Configure SMTP relay via Listmonk
curl -s -X PATCH "${API_BASE}/settings" -H "${auth_header}" -H "${ct}" \
  -d '{
    "smtp_host": "omni-listmonk",
    "smtp_port": 25,
    "smtp_from": "scheduling@omni-quantum.local"
  }'

# Event Type 1: 30-min Discovery Call
curl -s -X POST "${API_BASE}/event-types" -H "${auth_header}" -H "${ct}" \
  -d '{
    "title": "30-min Discovery Call",
    "slug": "discovery-30",
    "length": 30,
    "bufferTime": {"before": 15, "after": 15},
    "price": 0,
    "currency": "usd",
    "schedulingType": "ROUND_ROBIN",
    "availability": {
      "days": [1,2,3,4,5],
      "startTime": "09:00",
      "endTime": "17:00"
    },
    "description": "Introductory call to discuss your project needs and how we can help.",
    "locations": [{"type": "integrations:google:meet"}]
  }'

# Event Type 2: 60-min Project Planning
curl -s -X POST "${API_BASE}/event-types" -H "${auth_header}" -H "${ct}" \
  -d '{
    "title": "60-min Project Planning",
    "slug": "planning-60",
    "length": 60,
    "bufferTime": {"before": 30, "after": 30},
    "price": 0,
    "currency": "usd",
    "periodType": "ROLLING",
    "periodDays": 7,
    "periodCountCalendarDays": true,
    "limit": {"frequency": "week", "count": 3},
    "availability": {
      "days": [1,2,3,4,5],
      "startTime": "10:00",
      "endTime": "16:00"
    },
    "description": "Deep-dive into project requirements, architecture, and timeline planning.",
    "locations": [{"type": "integrations:google:meet"}]
  }'

# Event Type 3: 2-hour Technical Workshop
curl -s -X POST "${API_BASE}/event-types" -H "${auth_header}" -H "${ct}" \
  -d '{
    "title": "2-hour Technical Workshop",
    "slug": "workshop-120",
    "length": 120,
    "bufferTime": {"before": 60, "after": 60},
    "price": 0,
    "currency": "usd",
    "periodType": "ROLLING",
    "periodDays": 7,
    "periodCountCalendarDays": true,
    "limit": {"frequency": "week", "count": 2},
    "requiresConfirmation": true,
    "availability": {
      "days": [1,2,3,4,5],
      "startTime": "09:00",
      "endTime": "17:00"
    },
    "description": "Hands-on technical workshop. Requires prior appointment confirmation.",
    "locations": [{"type": "integrations:google:meet"}]
  }'

# Configure out-of-office
curl -s -X POST "${API_BASE}/out-of-office" -H "${auth_header}" -H "${ct}" \
  -d '{
    "enabled": true,
    "message": "Currently unavailable. Will respond upon return."
  }'

# Webhooks
create_webhook "booking.created" "${N8N_BASE}/booking-created"
create_webhook "booking.cancelled" "${N8N_BASE}/booking-cancelled"
create_webhook "booking.rescheduled" "${N8N_BASE}/booking-rescheduled"

notify_mm "#general" "Cal.com initialized: 3 event types, webhooks configured, SMTP relay via Listmonk."
echo "Cal.com init complete."
