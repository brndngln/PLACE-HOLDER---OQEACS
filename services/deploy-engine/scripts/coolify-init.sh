#!/usr/bin/env bash
set -euo pipefail

API_BASE="http://omni-coolify:8000/api/v1"
TOKEN="${COOLIFY_API_TOKEN}"
N8N_BASE="http://omni-n8n:5678/webhook"
MM_WEBHOOK="http://omni-mattermost-webhook:8066"

OIDC_CLIENT_ID=$(vault kv get -field=client_id secret/authentik/coolify)
OIDC_CLIENT_SECRET=$(vault kv get -field=client_secret secret/authentik/coolify)

VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_ROLE_ID=$(vault kv get -field=role_id secret/coolify/vault-approle)
VAULT_SECRET_ID=$(vault kv get -field=secret_id secret/coolify/vault-approle)

until curl -sf http://omni-coolify:8000/health; do sleep 3; done

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
    \"oidc_discovery_url\": \"http://omni-authentik:9000/application/o/coolify/.well-known/openid-configuration\"
  }"

# Add local Docker host
curl -s -X POST "${API_BASE}/servers" -H "${auth_header}" -H "${ct}" \
  -d '{
    "name": "local-docker",
    "ip": "host.docker.internal",
    "type": "docker",
    "is_localhost": true
  }'

# Create environments
for env in staging production; do
  curl -s -X POST "${API_BASE}/environments" -H "${auth_header}" -H "${ct}" \
    -d "{\"name\":\"${env}\"}"
done

# Resource limits per env
STAGING_LIMITS='{"cpu_limit":"1.0","memory_limit":"1g"}'
PROD_LIMITS='{"cpu_limit":"4.0","memory_limit":"4g"}'

# Common env vars for all templates
COMMON_ENV_VARS="VAULT_ADDR=${VAULT_ADDR}\nVAULT_ROLE_ID=${VAULT_ROLE_ID}\nVAULT_SECRET_ID=${VAULT_SECRET_ID}"

# Template: python-fastapi
curl -s -X POST "${API_BASE}/applications" -H "${auth_header}" -H "${ct}" \
  -d "{
    \"name\": \"python-fastapi\",
    \"is_template\": true,
    \"build_pack\": \"dockerfile\",
    \"dockerfile_location\": \"/Dockerfile\",
    \"health_check_path\": \"/health\",
    \"health_check_interval\": 30,
    \"health_check_retries\": 3,
    \"auto_deploy\": true,
    \"auto_deploy_branch\": \"main\",
    \"deploy_strategy\": \"blue-green\",
    \"auto_rollback\": true,
    \"rollback_window_seconds\": 300,
    \"env_vars\": \"${COMMON_ENV_VARS}\",
    \"traefik_labels\": {
      \"traefik.enable\": \"true\",
      \"traefik.http.routers.{app}.rule\": \"Host(\\\"{domain}\\\")\",
      \"traefik.http.routers.{app}.tls.certresolver\": \"letsencrypt\"
    },
    \"logging\": {\"driver\": \"json-file\", \"options\": {\"max-size\": \"50m\"}},
    \"resource_limits_staging\": ${STAGING_LIMITS},
    \"resource_limits_production\": ${PROD_LIMITS}
  }"

# Template: typescript-nextjs
curl -s -X POST "${API_BASE}/applications" -H "${auth_header}" -H "${ct}" \
  -d "{
    \"name\": \"typescript-nextjs\",
    \"is_template\": true,
    \"build_pack\": \"dockerfile\",
    \"dockerfile_location\": \"/Dockerfile\",
    \"health_check_path\": \"/\",
    \"health_check_interval\": 30,
    \"health_check_retries\": 3,
    \"auto_deploy\": true,
    \"auto_deploy_branch\": \"main\",
    \"deploy_strategy\": \"blue-green\",
    \"auto_rollback\": true,
    \"rollback_window_seconds\": 300,
    \"env_vars\": \"${COMMON_ENV_VARS}\",
    \"traefik_labels\": {
      \"traefik.enable\": \"true\",
      \"traefik.http.routers.{app}.rule\": \"Host(\\\"{domain}\\\")\",
      \"traefik.http.routers.{app}.tls.certresolver\": \"letsencrypt\"
    },
    \"logging\": {\"driver\": \"json-file\", \"options\": {\"max-size\": \"50m\"}},
    \"resource_limits_staging\": ${STAGING_LIMITS},
    \"resource_limits_production\": ${PROD_LIMITS}
  }"

# Template: static-site
curl -s -X POST "${API_BASE}/applications" -H "${auth_header}" -H "${ct}" \
  -d "{
    \"name\": \"static-site\",
    \"is_template\": true,
    \"build_pack\": \"nginx\",
    \"health_check_path\": \"/\",
    \"health_check_interval\": 30,
    \"health_check_retries\": 3,
    \"auto_deploy\": true,
    \"auto_deploy_branch\": \"main\",
    \"deploy_strategy\": \"blue-green\",
    \"auto_rollback\": true,
    \"rollback_window_seconds\": 300,
    \"env_vars\": \"${COMMON_ENV_VARS}\",
    \"traefik_labels\": {
      \"traefik.enable\": \"true\",
      \"traefik.http.routers.{app}.rule\": \"Host(\\\"{domain}\\\")\",
      \"traefik.http.routers.{app}.tls.certresolver\": \"letsencrypt\"
    },
    \"logging\": {\"driver\": \"json-file\", \"options\": {\"max-size\": \"50m\"}},
    \"resource_limits_staging\": ${STAGING_LIMITS},
    \"resource_limits_production\": ${PROD_LIMITS}
  }"

# Template: docker-compose
curl -s -X POST "${API_BASE}/applications" -H "${auth_header}" -H "${ct}" \
  -d "{
    \"name\": \"docker-compose\",
    \"is_template\": true,
    \"build_pack\": \"docker-compose\",
    \"health_check_path\": \"configurable\",
    \"health_check_interval\": 30,
    \"health_check_retries\": 3,
    \"auto_deploy\": false,
    \"deploy_strategy\": \"blue-green\",
    \"auto_rollback\": true,
    \"rollback_window_seconds\": 300,
    \"env_vars\": \"${COMMON_ENV_VARS}\",
    \"traefik_labels\": {
      \"traefik.enable\": \"true\",
      \"traefik.http.routers.{app}.rule\": \"Host(\\\"{domain}\\\")\",
      \"traefik.http.routers.{app}.tls.certresolver\": \"letsencrypt\"
    },
    \"logging\": {\"driver\": \"json-file\", \"options\": {\"max-size\": \"50m\"}},
    \"resource_limits_staging\": ${STAGING_LIMITS},
    \"resource_limits_production\": ${PROD_LIMITS}
  }"

# Webhooks for build/deploy events
create_webhook "build.started" "${N8N_BASE}/coolify-build-started"
create_webhook "build.completed" "${N8N_BASE}/coolify-build-completed"
create_webhook "build.failed" "${N8N_BASE}/coolify-build-failed"
create_webhook "deploy.started" "${N8N_BASE}/coolify-deploy-started"
create_webhook "deploy.completed" "${N8N_BASE}/coolify-deploy-completed"
create_webhook "deploy.failed" "${N8N_BASE}/coolify-deploy-failed"

notify_mm "#deployments" "Coolify initialized: 4 app templates, staging + production envs, blue-green deploy enabled."
echo "Coolify init complete."
