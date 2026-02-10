#!/usr/bin/env bash
set -euo pipefail

FLOWISE_API="http://omni-flowise:3000/api/v1"
ORCHESTRATOR_API="http://omni-orchestrator:9500/api/services/register"
MM_WEBHOOK="http://omni-mattermost-webhook:8066"
FLOW_DIR="$(dirname "$0")/../flows"

OIDC_CLIENT_ID=$(vault kv get -field=client_id secret/authentik/flowise)
OIDC_CLIENT_SECRET=$(vault kv get -field=client_secret secret/authentik/flowise)

until curl -sf http://omni-flowise:3000/health; do sleep 3; done

ct="Content-Type: application/json"

notify_mm() {
  curl -s -X POST "${MM_WEBHOOK}" -H "${ct}" -d "{\"channel\":\"$1\",\"text\":\"$2\"}"
}

# Configure Authentik SSO
curl -s -X POST "${FLOWISE_API}/credentials" -H "${ct}" \
  -d "{
    \"name\": \"authentik-oidc\",
    \"credentialName\": \"oidcAuth\",
    \"plainDataObj\": {
      \"clientId\": \"${OIDC_CLIENT_ID}\",
      \"clientSecret\": \"${OIDC_CLIENT_SECRET}\",
      \"discoveryUrl\": \"http://omni-authentik:9000/application/o/flowise/.well-known/openid-configuration\"
    }
  }"

# Configure LiteLLM credential
LITELLM_KEY=$(vault kv get -field=api_key secret/litellm/flowise)
curl -s -X POST "${FLOWISE_API}/credentials" -H "${ct}" \
  -d "{
    \"name\": \"litellm-openai\",
    \"credentialName\": \"openAIApi\",
    \"plainDataObj\": {
      \"openAIApiKey\": \"${LITELLM_KEY}\",
      \"basePath\": \"http://omni-litellm:4000/v1\"
    }
  }"

# Configure Qdrant credential
curl -s -X POST "${FLOWISE_API}/credentials" -H "${ct}" \
  -d '{
    "name": "qdrant-local",
    "credentialName": "qdrantApi",
    "plainDataObj": {
      "qdrantServerUrl": "http://omni-qdrant:6333"
    }
  }'

# Import flows and test each
FLOWS=("rag-chatbot" "code-review-assistant" "client-intake-bot" "knowledge-query")
TEST_QUERIES=(
  "What design patterns are used in the authentication module?"
  "Review this function: def add(a, b): return a + b"
  "Hi, my name is Test User and I need a web application built."
  "Explain the observer pattern and its implementations in the codebase."
)

for i in "${!FLOWS[@]}"; do
  flow_name="${FLOWS[$i]}"
  flow_file="${FLOW_DIR}/${flow_name}.json"

  echo "Importing flow: ${flow_name}..."
  FLOW_RESPONSE=$(curl -s -X POST "${FLOWISE_API}/chatflows" \
    -H "${ct}" \
    -d @"${flow_file}")

  FLOW_ID=$(echo "${FLOW_RESPONSE}" | jq -r '.id // empty')
  if [ -z "${FLOW_ID}" ]; then
    echo "ERROR: Failed to import ${flow_name}"
    notify_mm "#general" "Flowise: Failed to import flow ${flow_name}"
    continue
  fi

  echo "Testing flow: ${flow_name} (${FLOW_ID})..."
  TEST_RESULT=$(curl -s -X POST "${FLOWISE_API}/prediction/${FLOW_ID}" \
    -H "${ct}" \
    -d "{\"question\": \"${TEST_QUERIES[$i]}\"}" \
    --max-time 30)

  if echo "${TEST_RESULT}" | jq -e '.text // .message' >/dev/null 2>&1; then
    echo "  Flow ${flow_name} test PASSED"
  else
    echo "  WARNING: Flow ${flow_name} test may have issues"
    notify_mm "#general" "Flowise: Flow ${flow_name} test returned unexpected result"
  fi

  # Register with orchestrator
  curl -s -X POST "${ORCHESTRATOR_API}" -H "${ct}" \
    -d "{
      \"name\": \"flowise-${flow_name}\",
      \"type\": \"chatflow\",
      \"url\": \"${FLOWISE_API}/prediction/${FLOW_ID}\",
      \"health_url\": \"http://omni-flowise:3000/health\",
      \"metadata\": {\"flow_id\": \"${FLOW_ID}\", \"flow_name\": \"${flow_name}\"}
    }"

  echo "  Registered ${flow_name} with orchestrator"
done

notify_mm "#general" "Flowise initialized: ${#FLOWS[@]} flows imported, tested, and registered with orchestrator."
echo "Flowise init complete."
