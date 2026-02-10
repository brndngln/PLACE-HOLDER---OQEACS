#!/usr/bin/env bash
# ===========================================================================
# SYSTEM 33 — CRYPTOGRAPHIC FORTRESS PRO: SOPS Encrypt Script
# Omni Quantum Elite AI Coding System — Security & Identity Layer
#
# Encrypts a file in place using Mozilla SOPS + Age encryption.
# The Age key is fetched from Vault at runtime.
#
# Usage:
#   ./encrypt.sh <file-path>
#   ./encrypt.sh --all <directory>   # Encrypt all eligible files
# ===========================================================================

set -euo pipefail

# ───────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOPS_CONFIG="${SCRIPT_DIR}/sops-config.yaml"
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
AGE_KEY_VAULT_PATH="${AGE_KEY_VAULT_PATH:-sops/age-key}"
VAULT_MOUNT="${VAULT_MOUNT:-secret}"

# Files/patterns to skip
SKIP_PATTERNS=(
    "docker-compose*.yml"
    "*.md"
    "*.sh"
    "Makefile"
    ".gitignore"
    "Dockerfile*"
    "*.tar.gz"
    "*.zip"
    "*.png"
    "*.jpg"
    "*.ico"
)

# ───────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────

log() { echo "[encrypt] $*"; }
error() { echo "[encrypt] ERROR: $*" >&2; }

should_skip() {
    local filename
    filename="$(basename "$1")"
    for pattern in "${SKIP_PATTERNS[@]}"; do
        # shellcheck disable=SC2254
        case "$filename" in
            $pattern) return 0 ;;
        esac
    done
    return 1
}

is_already_encrypted() {
    local file="$1"
    # SOPS-encrypted files contain the "sops" metadata key
    if grep -q '"sops"' "$file" 2>/dev/null || grep -q 'sops:' "$file" 2>/dev/null; then
        return 0
    fi
    return 1
}

# ───────────────────────────────────────────────────────────────────────
# Fetch Age public key from Vault
# ───────────────────────────────────────────────────────────────────────

fetch_age_recipients() {
    if [ -n "${SOPS_AGE_RECIPIENTS:-}" ]; then
        return 0
    fi

    if [ -z "$VAULT_TOKEN" ]; then
        error "VAULT_TOKEN must be set (or set SOPS_AGE_RECIPIENTS directly)"
        exit 1
    fi

    log "Fetching Age public key from Vault ..."
    local vault_response
    vault_response=$(curl -sf \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/${VAULT_MOUNT}/data/${AGE_KEY_VAULT_PATH}" 2>/dev/null)

    if [ -z "$vault_response" ]; then
        error "Could not read Age key from Vault at ${AGE_KEY_VAULT_PATH}"
        exit 1
    fi

    export SOPS_AGE_RECIPIENTS
    SOPS_AGE_RECIPIENTS=$(echo "$vault_response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data['data']['data']['public_key'])
" 2>/dev/null)

    if [ -z "$SOPS_AGE_RECIPIENTS" ]; then
        error "Age public key not found in Vault response"
        exit 1
    fi

    log "Age recipient: ${SOPS_AGE_RECIPIENTS:0:20}..."
}

# ───────────────────────────────────────────────────────────────────────
# Encrypt a single file
# ───────────────────────────────────────────────────────────────────────

encrypt_file() {
    local file="$1"

    if [ ! -f "$file" ]; then
        error "File not found: $file"
        return 1
    fi

    if should_skip "$file"; then
        log "Skipping (excluded pattern): $file"
        return 0
    fi

    if is_already_encrypted "$file"; then
        log "Already encrypted: $file"
        return 0
    fi

    log "Encrypting: $file"
    sops --config "$SOPS_CONFIG" --encrypt --in-place "$file"
    log "  Encrypted successfully"
}

# ───────────────────────────────────────────────────────────────────────
# Encrypt all eligible files in a directory
# ───────────────────────────────────────────────────────────────────────

encrypt_directory() {
    local dir="$1"
    local count=0

    log "Encrypting eligible files in: $dir"

    # .env files
    while IFS= read -r -d '' file; do
        encrypt_file "$file"
        count=$((count + 1))
    done < <(find "$dir" -name '.env' -o -name '.env.*' -print0 2>/dev/null)

    # YAML config files
    while IFS= read -r -d '' file; do
        encrypt_file "$file"
        count=$((count + 1))
    done < <(find "$dir" -path '*/config/*.yml' -o -path '*/config/*.yaml' -print0 2>/dev/null)

    # tfvars
    while IFS= read -r -d '' file; do
        encrypt_file "$file"
        count=$((count + 1))
    done < <(find "$dir" -name '*.tfvars' -print0 2>/dev/null)

    log "Processed $count files"
}

# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────

main() {
    if [ $# -lt 1 ]; then
        echo "Usage: $0 <file-path>"
        echo "       $0 --all <directory>"
        exit 1
    fi

    # Verify sops is installed
    if ! command -v sops &> /dev/null; then
        error "sops is not installed. Install from https://github.com/getsops/sops"
        exit 1
    fi

    fetch_age_recipients

    if [ "$1" = "--all" ]; then
        local dir="${2:-.}"
        encrypt_directory "$dir"
    else
        encrypt_file "$1"
    fi
}

main "$@"
