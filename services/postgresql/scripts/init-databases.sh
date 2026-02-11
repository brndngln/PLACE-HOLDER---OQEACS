#!/usr/bin/env bash
set -euo pipefail

DATABASES=(
  "financial_fortress"
  "langfuse"
  "litellm"
  "woodpecker"
  "coder"
  "formbricks"
  "mlflow"
  "pact"
  "sla_tracker"
  "omni_orchestrator"
  "tolgee"
  "gitea"
  "mattermost"
  "n8n"
  "authentik"
  "superset"
  "calcom"
  "kong"
  "posthog"
  "chatwoot"
  "glitchtip"
)

ensure_role() {
  local role_name="$1"
  local role_password="$2"

  psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname postgres <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${role_name}') THEN
    EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', '${role_name}', '${role_password}');
  END IF;
END
\$\$;
SQL
}

ensure_database() {
  local db_name="$1"
  local owner_name="$2"

  if ! psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${db_name}'" | grep -q 1; then
    psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname postgres -c "CREATE DATABASE \"${db_name}\" OWNER \"${owner_name}\";"
  fi
}

enable_extensions() {
  local db_name="$1"
  psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${db_name}" -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
  psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${db_name}" -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm;'
}

echo "Ensuring Omni PostgreSQL databases and roles..."

for db_name in "${DATABASES[@]}"; do
  user_name="${db_name}"
  password_var="$(echo "${db_name}_PASSWORD" | tr '[:lower:]-' '[:upper:]_')"
  user_password="${!password_var:-${POSTGRES_PASSWORD}}"

  ensure_role "${user_name}" "${user_password}"
  ensure_database "${db_name}" "${user_name}"
  enable_extensions "${db_name}"

  echo "Ensured database '${db_name}' with owner '${user_name}'."
done

echo "Database initialization complete."
