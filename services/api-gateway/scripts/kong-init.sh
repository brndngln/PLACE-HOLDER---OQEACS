#!/usr/bin/env bash
set -Eeuo pipefail

KONG_ADMIN_URL="${KONG_ADMIN_URL:-http://omni-kong:8001}"
MM_WEBHOOK="${MM_WEBHOOK:-http://omni-mattermost-webhook:8066/hooks/builds}"
AUDIT_URL="${AUDIT_URL:-http://omni-audit-logger:9550/events}"
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-*}"

wait_for_kong() {
  for _ in $(seq 1 120); do
    curl -fsS "${KONG_ADMIN_URL}/status" >/dev/null && return 0
    sleep 2
  done
  echo "[kong-init] Kong did not become healthy in time" >&2
  exit 1
}

api() {
  curl -fsS -H "Content-Type: application/json" "$@"
}

service_exists() {
  local name="$1"
  curl -fsS "${KONG_ADMIN_URL}/services/${name}" >/dev/null 2>&1
}

route_exists() {
  local name="$1"
  curl -fsS "${KONG_ADMIN_URL}/routes/${name}" >/dev/null 2>&1
}

ensure_service() {
  local name="$1" url="$2"
  if service_exists "$name"; then
    api -X PATCH "${KONG_ADMIN_URL}/services/${name}" -d "{\"url\":\"${url}\"}" >/dev/null
  else
    api -X POST "${KONG_ADMIN_URL}/services" -d "{\"name\":\"${name}\",\"url\":\"${url}\"}" >/dev/null
  fi
}

ensure_route() {
  local route_name="$1" service_name="$2" path="$3"
  if route_exists "$route_name"; then
    api -X PATCH "${KONG_ADMIN_URL}/routes/${route_name}" -d "{\"paths\":[\"${path}\"],\"strip_path\":false,\"service\":{\"name\":\"${service_name}\"}}" >/dev/null
  else
    api -X POST "${KONG_ADMIN_URL}/services/${service_name}/routes" -d "{\"name\":\"${route_name}\",\"paths\":[\"${path}\"],\"strip_path\":false}" >/dev/null
  fi
}

ensure_plugin() {
  local endpoint="$1" plugin_name="$2" payload="$3"
  local existing
  existing="$(curl -fsS "${KONG_ADMIN_URL}${endpoint}" 2>/dev/null || echo '{}')"
  if echo "$existing" | grep -q "\"name\":\"${plugin_name}\""; then
    return 0
  fi
  api -X POST "${KONG_ADMIN_URL}${endpoint}" -d "$payload" >/dev/null || true
}

ensure_consumer() {
  local username="$1" custom_id="$2"
  if curl -fsS "${KONG_ADMIN_URL}/consumers/${username}" >/dev/null 2>&1; then
    return 0
  fi
  api -X POST "${KONG_ADMIN_URL}/consumers" -d "{\"username\":\"${username}\",\"custom_id\":\"${custom_id}\"}" >/dev/null || true
}

ensure_api_key() {
  local consumer="$1"
  local out
  out="$(curl -fsS "${KONG_ADMIN_URL}/consumers/${consumer}/key-auth" 2>/dev/null || echo '{}')"
  if echo "$out" | grep -q '"total"'; then
    return 0
  fi
  api -X POST "${KONG_ADMIN_URL}/consumers/${consumer}/key-auth" -d '{}' >/dev/null || true
}

wait_for_kong

kong migrations bootstrap -v || true
kong migrations up -v || true
kong migrations finish -v || true

ensure_service client-api-service http://omni-orchestrator:9500/api/client
ensure_service webhook-service http://omni-mattermost-webhook:8066
ensure_service chatbot-service http://omni-flowise:3000/api/v1/prediction
ensure_service schedule-service http://omni-calcom:3000/api
ensure_service status-service http://omni-uptime-kuma:3001/api

ensure_route projects-route client-api-service /api/v1/projects
ensure_route webhooks-route webhook-service /api/v1/webhooks
ensure_route chat-route chatbot-service /api/v1/chat
ensure_route schedule-route schedule-service /api/v1/schedule
ensure_route status-route status-service /api/v1/status

ensure_plugin /plugins key-auth '{"name":"key-auth","config":{"key_names":["X-API-Key"],"hide_credentials":true}}'
ensure_plugin /plugins rate-limiting '{"name":"rate-limiting","config":{"minute":100,"policy":"local","limit_by":"consumer","hide_client_headers":false}}'
ensure_plugin /routes/chat-route/plugins rate-limiting '{"name":"rate-limiting","config":{"minute":30,"policy":"local","limit_by":"consumer"}}'
ensure_plugin /routes/webhooks-route/plugins rate-limiting '{"name":"rate-limiting","config":{"minute":500,"policy":"local","limit_by":"ip"}}'
ensure_plugin /plugins cors "{\"name\":\"cors\",\"config\":{\"origins\":[\"${ALLOWED_ORIGINS}\"],\"methods\":[\"GET\",\"POST\",\"PUT\",\"DELETE\",\"OPTIONS\"],\"headers\":[\"Content-Type\",\"Authorization\",\"X-API-Key\"],\"max_age\":3600}}"
ensure_plugin /plugins request-size-limiting '{"name":"request-size-limiting","config":{"allowed_payload_size":10}}'
ensure_plugin /routes/chat-route/plugins request-size-limiting '{"name":"request-size-limiting","config":{"allowed_payload_size":1}}'
ensure_plugin /routes/webhooks-route/plugins request-size-limiting '{"name":"request-size-limiting","config":{"allowed_payload_size":5}}'
ensure_plugin /plugins response-transformer '{"name":"response-transformer","config":{"remove":{"headers":["X-Internal-*","X-Forwarded-*"]},"add":{"headers":["X-Response-Time:0"]}}}'
ensure_plugin /plugins prometheus '{"name":"prometheus"}'
ensure_plugin /plugins http-log "{\"name\":\"http-log\",\"config\":{\"http_endpoint\":\"${AUDIT_URL}\",\"method\":\"POST\",\"content_type\":\"application/json\"}}"

ensure_consumer client-standard client-standard
ensure_consumer client-premium client-premium
ensure_consumer internal internal
ensure_api_key client-standard
ensure_api_key client-premium
ensure_api_key internal

curl -fsS -X POST "${MM_WEBHOOK}" -H "Content-Type: application/json" -d '{"text":"[omni-kong] init complete: idempotent services/routes/plugins/consumers configured"}' || true
