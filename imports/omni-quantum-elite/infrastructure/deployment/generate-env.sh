#!/bin/bash
#
# generate-env.sh
#
# This script populates a `.env` file with secret values required
# across the entire Omni platform. It is designed to be idempotent:
# running it multiple times will never overwrite existing keys in
# `.env` or secrets already stored in Vault. Missing values are pulled
# from Vault when available or generated locally using OpenSSL. New
# secrets are automatically pushed back to Vault for safekeeping.
#
# Usage:
#   bash scripts/generate-env.sh
#
# The script assumes that the Vault CLI is installed and configured
# appropriately (i.e. `VAULT_ADDR` and authentication token are set).
# If Vault is unavailable or a key does not exist in Vault, a new
# random value is generated.

set -euo pipefail

# Location of the output env file
ENV_FILE=".env"

# Ensure the scripts directory exists when run from project root
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Create .env if it does not yet exist
if [[ ! -f "$ENV_FILE" ]]; then
  touch "$ENV_FILE"
fi

# Helper: print message with consistent prefix
log() {
  local level="$1"
  shift
  printf '[%s] %s\n' "$level" "$*"
}

# Helper: safely retrieve a secret from Vault. Returns empty string
# if the key does not exist or Vault is unreachable.
vault_get() {
  local path="$1"
  local field="$2"
  local value=""
  # Attempt to fetch the secret only if the vault CLI is available
  if command -v vault >/dev/null 2>&1; then
    # Suppress error output to avoid confusing log messages
    if value=$(vault kv get -field="$field" "$path" 2>/dev/null); then
      echo "$value"
      # Always return 0 to prevent set -e from aborting
      return 0
    fi
  fi
  # Return empty string on failure
  echo ""
  # Always return success status; absence of a key is not an error
  return 0
}

# Helper: store a secret in Vault at the given path.
vault_put() {
  local path="$1"
  local field="$2"
  local value="$3"
  if command -v vault >/dev/null 2>&1; then
    # shellcheck disable=SC2086
    vault kv put "$path" "$field=$value" >/dev/null 2>&1 || true
  fi
}

# Helper: generate a 32-byte hex secret using OpenSSL
generate_secret() {
  openssl rand -hex 32
}

# Helper: ensure a key exists in the .env file. Looks up the value
# in Vault first, then generates a new secret if absent. When a new
# secret is generated, it is stored back into Vault. The .env is
# appended if the key is missing; existing keys are preserved.
ensure_env_var() {
  local var_name="$1"
  local vault_path="$2"
  local vault_field="$3"
  local value=""

  # Skip if the variable already exists in the .env file
  if grep -q "^${var_name}=" "$ENV_FILE"; then
    return
  fi

  # Try to pull from Vault
  value=$(vault_get "$vault_path" "$vault_field")
  if [[ -z "$value" ]]; then
    # Generate a new secret
    value=$(generate_secret)
    # Store in Vault for future runs
    vault_put "$vault_path" "$vault_field" "$value"
  fi

  # Append to .env
  echo "${var_name}=${value}" >> "$ENV_FILE"
}

#
# Define the list of service identifiers. These correspond to the
# various platform systems. If you add or remove services in other
# parts of the platform, update this list accordingly.
SERVICES=(
  # Tier 0 / Infrastructure
  postgres redis minio
  # Tier 1 / Core Services
  vault traefik authentik prometheus loki grafana
  # Tier 2 / Developer Tools
  ollama litellm gitea mattermost qdrant langfuse
  # Tier 3 / Integration & Orchestration
  n8n plane nango flowise wikijs superset calcom
  # Tier 4 / Advanced Systems
  openhands swe_agent token_infinity omi_bridge
  # Tier 5 / Pro Series (Systems 29-34)
  pulse_command_pro log_nexus_pro guardian_eye backup_fortress_pro cryptographic_fortress_pro gateway_sentinel_pro
  # System 35 & 36
  build_forge code_forge
  # System 37
  omni_command
)

# For each service, define the set of secrets to create. These names
# will be combined with the service identifier to form the final
# environment variable name. For example, service `gitea` with
# secret type `db_password` becomes `GITEA_DB_PASSWORD`.
SECRET_TYPES=(
  db_password
  redis_password
  api_token
  webhook_url
  oauth_secret
)

# Iterate through each service and secret type to ensure variables exist
for svc in "${SERVICES[@]}"; do
  svc_upper=$(echo "$svc" | tr '[:lower:]' '[:upper:]')
  for stype in "${SECRET_TYPES[@]}"; do
    # Construct the variable name (uppercase and underscores)
    var_name="${svc_upper}_$(echo "$stype" | tr '[:lower:]' '[:upper:]')"
    # Construct a Vault path. Group secrets by service to keep them
    # organized under `secret/data/omni/{service}`. The field name is
    # the original secret type.
    vault_path="secret/data/omni/${svc}"
    vault_field="${stype}"
    ensure_env_var "$var_name" "$vault_path" "$vault_field"
  done
done

# Global secrets that aren't tied to a specific service can be defined
# individually below. These cover shared credentials such as database
# superuser passwords or platform-wide tokens. Feel free to add more
# global variables here as required by other scripts.

GLOBAL_VARS=(
  POSTGRES_ROOT_PASSWORD
  REDIS_ROOT_PASSWORD
  MINIO_ROOT_USER
  MINIO_ROOT_PASSWORD
  VAULT_ROOT_TOKEN
  AUTHENTIK_SECRET_KEY
  GRAFANA_ADMIN_PASSWORD
  PROMETHEUS_ADMIN_TOKEN
)

for gvar in "${GLOBAL_VARS[@]}"; do
  # Use a simplified Vault path for globals
  vault_path="secret/data/omni/globals"
  vault_field="${gvar,,}"
  ensure_env_var "$gvar" "$vault_path" "$vault_field"
done

# Report the number of variables generated to the user
total_vars=$(grep -c '=' "$ENV_FILE" || true)
log "INFO" "Environment generation complete: $total_vars variables present in $ENV_FILE"

exit 0