#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE_FILE="${ROOT_DIR}/.env.example"
TMP_VARS="$(mktemp)"

collect_vars() {
  grep -Rho '\${[A-Z_][A-Z0-9_]*\(:-[^}]*\)*}' \
    "${ROOT_DIR}/services" "${ROOT_DIR}/omni-quantum-systems" "${ROOT_DIR}/financial" "${ROOT_DIR}/docker-compose.yml" \
    --include='*.yml' --include='*.yaml' 2>/dev/null \
    | sed -E 's/^\$\{([A-Z_][A-Z0-9_]*).*/\1/' \
    | sort -u > "${TMP_VARS}"
}

is_secret_key() {
  case "$1" in
    *PASSWORD*|*SECRET*|*TOKEN*|*KEY*|*PRIVATE*|*PASSPHRASE*) return 0 ;;
    *) return 1 ;;
  esac
}

default_value_for_var() {
  local var="$1"

  if is_secret_key "$var"; then
    openssl rand -base64 32 | tr -d '\n'
    return
  fi

  case "$var" in
    *URL) echo "http://placeholder:0000" ;;
    *HOST) echo "omni-placeholder" ;;
    *PORT) echo "0000" ;;
    LOG_LEVEL) echo "info" ;;
    LOG_FORMAT) echo "json" ;;
    VERSION) echo "1.0.0" ;;
    BUILD_DATE) date -u +"%Y-%m-%dT%H:%M:%SZ" ;;
    SERVICE_NAME*|SERVICE_PORT*) echo "CHANGEME" ;;
    *) echo "CHANGEME" ;;
  esac
}

ensure_env_file() {
  touch "${ENV_FILE}"
}

merge_into_env() {
  local var val
  while IFS= read -r var; do
    [[ -z "$var" ]] && continue
    if ! grep -q "^${var}=" "${ENV_FILE}"; then
      val="$(default_value_for_var "$var")"
      printf '%s=%s\n' "$var" "$val" >> "${ENV_FILE}"
    fi
  done < "${TMP_VARS}"
}

build_env_example() {
  {
    echo "# ═══════════════════════════════════════════════════════════════"
    echo "# OMNI QUANTUM ELITE — MASTER ENVIRONMENT CONFIGURATION"
    echo "# Copy to .env and fill in real values. NEVER commit .env to git."
    echo "# ═══════════════════════════════════════════════════════════════"
    echo
    echo "# ── FOUNDATION INFRASTRUCTURE ──"
    echo "POSTGRES_USER=omni_admin"
    echo "POSTGRES_PASSWORD=CHANGE_ME_GENERATE_WITH_OPENSSL"
    echo "POSTGRES_HOST=omni-postgres"
    echo "POSTGRES_PORT=5432"
    echo "POSTGRES_DB=omni_master"
    echo "REDIS_HOST=omni-redis"
    echo "REDIS_PORT=6379"
    echo "REDIS_PASSWORD=CHANGE_ME_GENERATE_WITH_OPENSSL"
    echo "REDIS_URL=redis://:\${REDIS_PASSWORD}@omni-redis:6379/0"
    echo
    echo "# ── PLATFORM VARIABLES (auto-collected) ──"
    while IFS= read -r var; do
      [[ -z "$var" ]] && continue
      if is_secret_key "$var"; then
        printf '%s=%s\n' "$var" "CHANGE_ME_GENERATE_WITH_OPENSSL"
      else
        printf '%s=%s\n' "$var" "CHANGEME"
      fi
    done < "${TMP_VARS}"
  } > "${ENV_EXAMPLE_FILE}"
}

collect_vars
ensure_env_file
merge_into_env
build_env_example

chmod 600 "${ENV_FILE}" 2>/dev/null || true

echo "Generated/updated: ${ENV_FILE} ($(grep -c '=' "${ENV_FILE}") vars)"
echo "Generated/updated: ${ENV_EXAMPLE_FILE} ($(grep -c '=' "${ENV_EXAMPLE_FILE}") vars)"

rm -f "${TMP_VARS}"
