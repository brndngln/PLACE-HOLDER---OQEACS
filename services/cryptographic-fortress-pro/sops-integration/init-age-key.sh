#!/usr/bin/env bash
# ===========================================================================
# SYSTEM 33 — CRYPTOGRAPHIC FORTRESS PRO: Age Key Initialization
# Omni Quantum Elite AI Coding System — Security & Identity Layer
#
# Generates an Age encryption keypair and stores it securely in Vault.
# This script should be run ONCE during initial platform setup.
#
# Prerequisites:
#   - age-keygen installed (apt install age or brew install age)
#   - Vault accessible and unsealed
#   - VAULT_ADDR, VAULT_ROLE_ID, VAULT_SECRET_ID set in environment or .env
#
# Usage:
#   ./init-age-key.sh
#   ./init-age-key.sh --force   # Overwrite existing key in Vault
# ===========================================================================

set -euo pipefail

# ───────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_ROLE_ID="${VAULT_ROLE_ID:-}"
VAULT_SECRET_ID="${VAULT_SECRET_ID:-}"
VAULT_SECRET_PATH="secret/data/sops/age"
FORCE_OVERWRITE=false

# ───────────────────────────────────────────────────────────────────────
# Colors & Logging
# ───────────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${BLUE}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')]${NC} $*"; }
info()  { echo -e "${GREEN}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ✅${NC} $*"; }
warn()  { echo -e "${YELLOW}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ⚠️${NC}  $*"; }
error() { echo -e "${RED}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ❌${NC} $*" >&2; }

# ───────────────────────────────────────────────────────────────────────
# Cleanup
# ───────────────────────────────────────────────────────────────────────

TEMP_KEYFILE=""
cleanup() {
    local exit_code=$?
    if [[ -n "${TEMP_KEYFILE}" && -f "${TEMP_KEYFILE}" ]]; then
        shred -u "${TEMP_KEYFILE}" 2>/dev/null || rm -f "${TEMP_KEYFILE}"
        log "Cleaned up temporary key file"
    fi
    unset VAULT_TOKEN 2>/dev/null || true
    if [[ ${exit_code} -ne 0 ]]; then
        error "Script failed with exit code ${exit_code}"
    fi
    exit ${exit_code}
}
trap cleanup EXIT INT TERM

# ───────────────────────────────────────────────────────────────────────
# Argument Parsing
# ───────────────────────────────────────────────────────────────────────

for arg in "$@"; do
    case "${arg}" in
        --force)
            FORCE_OVERWRITE=true
            warn "Force mode enabled — will overwrite existing key in Vault"
            ;;
        --help|-h)
            echo "Usage: $(basename "$0") [--force]"
            echo ""
            echo "Generates an Age encryption keypair and stores it in Vault."
            echo ""
            echo "Options:"
            echo "  --force    Overwrite existing key in Vault"
            echo "  --help     Show this help message"
            exit 0
            ;;
        *)
            error "Unknown argument: ${arg}"
            echo "Usage: $(basename "$0") [--force]"
            exit 1
            ;;
    esac
done

# ───────────────────────────────────────────────────────────────────────
# Load Environment
# ───────────────────────────────────────────────────────────────────────

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    log "Loading environment from ${PROJECT_ROOT}/.env"
    set -a
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Validate required variables
if [[ -z "${VAULT_ROLE_ID}" ]]; then
    error "VAULT_ROLE_ID is not set. Export it or add to .env"
    exit 1
fi

if [[ -z "${VAULT_SECRET_ID}" ]]; then
    error "VAULT_SECRET_ID is not set. Export it or add to .env"
    exit 1
fi

# ───────────────────────────────────────────────────────────────────────
# Prerequisite Checks
# ───────────────────────────────────────────────────────────────────────

log "Checking prerequisites..."

if ! command -v age-keygen &>/dev/null; then
    error "age-keygen is not installed. Install with: apt install age (or brew install age)"
    exit 1
fi
info "age-keygen found: $(age-keygen --version 2>&1 || echo 'unknown version')"

if ! command -v curl &>/dev/null; then
    error "curl is not installed"
    exit 1
fi

if ! command -v jq &>/dev/null; then
    error "jq is not installed"
    exit 1
fi

# ───────────────────────────────────────────────────────────────────────
# Phase 1: Wait for Vault
# ───────────────────────────────────────────────────────────────────────

log "Phase 1: Waiting for Vault at ${VAULT_ADDR}..."

MAX_WAIT=60
ELAPSED=0
while [[ ${ELAPSED} -lt ${MAX_WAIT} ]]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        "${VAULT_ADDR}/v1/sys/health" 2>/dev/null || echo "000")
    if [[ "${HTTP_CODE}" == "200" || "${HTTP_CODE}" == "429" ]]; then
        info "Vault is ready (HTTP ${HTTP_CODE})"
        break
    fi
    log "Vault not ready (HTTP ${HTTP_CODE}), waiting... (${ELAPSED}/${MAX_WAIT}s)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [[ ${ELAPSED} -ge ${MAX_WAIT} ]]; then
    error "Vault did not become ready within ${MAX_WAIT}s"
    exit 1
fi

# ───────────────────────────────────────────────────────────────────────
# Phase 2: Authenticate to Vault via AppRole
# ───────────────────────────────────────────────────────────────────────

log "Phase 2: Authenticating to Vault via AppRole..."

AUTH_RESPONSE=$(curl -s -X POST \
    "${VAULT_ADDR}/v1/auth/approle/login" \
    -H "Content-Type: application/json" \
    -d "{\"role_id\": \"${VAULT_ROLE_ID}\", \"secret_id\": \"${VAULT_SECRET_ID}\"}")

VAULT_TOKEN=$(echo "${AUTH_RESPONSE}" | jq -r '.auth.client_token // empty')

if [[ -z "${VAULT_TOKEN}" ]]; then
    error "Failed to authenticate to Vault via AppRole"
    error "Response: $(echo "${AUTH_RESPONSE}" | jq -r '.errors // empty')"
    exit 1
fi

export VAULT_TOKEN
info "Authenticated to Vault (token accessor: $(echo "${AUTH_RESPONSE}" | jq -r '.auth.accessor'))"

# ───────────────────────────────────────────────────────────────────────
# Phase 3: Check for Existing Key
# ───────────────────────────────────────────────────────────────────────

log "Phase 3: Checking for existing Age key in Vault at ${VAULT_SECRET_PATH}..."

EXISTING_KEY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    "${VAULT_ADDR}/v1/${VAULT_SECRET_PATH}" 2>/dev/null || echo "000")

if [[ "${EXISTING_KEY_RESPONSE}" == "200" ]]; then
    if [[ "${FORCE_OVERWRITE}" == "true" ]]; then
        warn "Existing Age key found in Vault — will overwrite (--force specified)"
    else
        EXISTING_PUBLIC=$(curl -s \
            -H "X-Vault-Token: ${VAULT_TOKEN}" \
            "${VAULT_ADDR}/v1/${VAULT_SECRET_PATH}" | jq -r '.data.data.age_public_key // empty')
        if [[ -n "${EXISTING_PUBLIC}" ]]; then
            info "Age key already exists in Vault"
            echo ""
            echo "══════════════════════════════════════════════════════════════"
            echo "  Age Public Key: ${EXISTING_PUBLIC}"
            echo "  Vault Path:     ${VAULT_SECRET_PATH}"
            echo "  Status:         Already configured"
            echo "══════════════════════════════════════════════════════════════"
            echo ""
            info "Use --force to regenerate and overwrite"
            exit 0
        fi
    fi
fi

# ───────────────────────────────────────────────────────────────────────
# Phase 4: Generate Age Keypair
# ───────────────────────────────────────────────────────────────────────

log "Phase 4: Generating Age keypair..."

TEMP_KEYFILE=$(mktemp /tmp/age-key-XXXXXXXXXX)
chmod 600 "${TEMP_KEYFILE}"

age-keygen -o "${TEMP_KEYFILE}" 2>/dev/null

# Parse public key from the comment line
PUBLIC_KEY=$(grep "^# public key:" "${TEMP_KEYFILE}" | awk '{print $NF}')

# Parse private key (non-comment, non-empty lines)
PRIVATE_KEY=$(grep -v "^#" "${TEMP_KEYFILE}" | grep -v "^$" | head -1)

if [[ -z "${PUBLIC_KEY}" || -z "${PRIVATE_KEY}" ]]; then
    error "Failed to parse Age keypair from keygen output"
    exit 1
fi

info "Age keypair generated successfully"
log "  Public key: ${PUBLIC_KEY}"

# ───────────────────────────────────────────────────────────────────────
# Phase 5: Store in Vault
# ───────────────────────────────────────────────────────────────────────

log "Phase 5: Storing Age keypair in Vault at ${VAULT_SECRET_PATH}..."

CREATED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
CREATED_BY=$(whoami 2>/dev/null || echo "system")
HOSTNAME_VAL=$(hostname 2>/dev/null || echo "unknown")

STORE_RESPONSE=$(curl -s -X POST \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    -H "Content-Type: application/json" \
    "${VAULT_ADDR}/v1/${VAULT_SECRET_PATH}" \
    -d "{
        \"data\": {
            \"age_public_key\": \"${PUBLIC_KEY}\",
            \"age_private_key\": \"${PRIVATE_KEY}\",
            \"created_at\": \"${CREATED_AT}\",
            \"created_by\": \"${CREATED_BY}\",
            \"created_on\": \"${HOSTNAME_VAL}\",
            \"key_type\": \"X25519\",
            \"purpose\": \"SOPS file encryption for Omni Quantum Elite platform\"
        },
        \"options\": {
            \"cas\": 0
        }
    }")

# Verify the write succeeded
WRITE_VERSION=$(echo "${STORE_RESPONSE}" | jq -r '.data.version // empty')

if [[ -z "${WRITE_VERSION}" ]]; then
    WRITE_ERRORS=$(echo "${STORE_RESPONSE}" | jq -r '.errors // empty')
    if [[ -n "${WRITE_ERRORS}" && "${WRITE_ERRORS}" != "null" ]]; then
        error "Failed to store Age key in Vault: ${WRITE_ERRORS}"
        exit 1
    fi
    warn "Could not verify write version, but no errors returned"
else
    info "Age key stored in Vault (version: ${WRITE_VERSION})"
fi

# ───────────────────────────────────────────────────────────────────────
# Phase 6: Verify Retrieval
# ───────────────────────────────────────────────────────────────────────

log "Phase 6: Verifying key retrieval from Vault..."

VERIFY_RESPONSE=$(curl -s \
    -H "X-Vault-Token: ${VAULT_TOKEN}" \
    "${VAULT_ADDR}/v1/${VAULT_SECRET_PATH}")

VERIFY_PUBLIC=$(echo "${VERIFY_RESPONSE}" | jq -r '.data.data.age_public_key // empty')
VERIFY_PRIVATE=$(echo "${VERIFY_RESPONSE}" | jq -r '.data.data.age_private_key // empty')

if [[ "${VERIFY_PUBLIC}" != "${PUBLIC_KEY}" ]]; then
    error "Verification FAILED: public key mismatch"
    exit 1
fi

if [[ -z "${VERIFY_PRIVATE}" ]]; then
    error "Verification FAILED: private key not retrievable"
    exit 1
fi

info "Key verification passed — read-back matches generated key"

# ───────────────────────────────────────────────────────────────────────
# Phase 7: Update SOPS Config
# ───────────────────────────────────────────────────────────────────────

SOPS_CONFIG="${SCRIPT_DIR}/sops-config.yaml"
if [[ -f "${SOPS_CONFIG}" ]]; then
    log "Phase 7: SOPS config found at ${SOPS_CONFIG}"
    log "  Set SOPS_AGE_RECIPIENT=${PUBLIC_KEY} in your environment"
    log "  Or update .sops.yaml in project root with the public key"
fi

# ───────────────────────────────────────────────────────────────────────
# Summary
# ───────────────────────────────────────────────────────────────────────

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  Age Key Initialization Complete"
echo "══════════════════════════════════════════════════════════════════"
echo ""
echo "  Public Key:     ${PUBLIC_KEY}"
echo "  Vault Path:     ${VAULT_SECRET_PATH}"
echo "  Vault Version:  ${WRITE_VERSION:-unknown}"
echo "  Created At:     ${CREATED_AT}"
echo "  Key Type:       X25519 (Age v1)"
echo ""
echo "  Next Steps:"
echo "    1. Export SOPS_AGE_RECIPIENT=${PUBLIC_KEY}"
echo "    2. Use ./encrypt.sh <file> to encrypt files"
echo "    3. Use ./decrypt.sh <file> to decrypt files"
echo "    4. Add public key to CI/CD environment variables"
echo ""
echo "  IMPORTANT:"
echo "    - The private key is stored ONLY in Vault"
echo "    - NEVER export or log the private key"
echo "    - Back up Vault unseal keys separately"
echo ""
echo "══════════════════════════════════════════════════════════════════"

info "Age key initialization complete"
exit 0
