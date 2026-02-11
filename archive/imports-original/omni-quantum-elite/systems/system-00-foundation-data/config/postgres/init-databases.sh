#!/bin/bash
###############################################################################
# Creates all databases required by platform services.
# Runs automatically on first PostgreSQL startup.
###############################################################################
set -e

DATABASES=(
  litellm authentik gitea n8n mattermost langfuse plane nango
  flowise wikijs superset calcom twenty crater coolify
  omni_orchestrator token_infinity
)

for db in "${DATABASES[@]}"; do
  echo "Creating database: $db"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-SQL
    SELECT 'CREATE DATABASE $db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
SQL
done

echo "✓ All databases initialized"
