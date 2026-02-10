#!/usr/bin/env bash
# ===========================================================================
# SYSTEM 33 — CRYPTOGRAPHIC FORTRESS PRO: SOPS Decrypt Script
# Omni Quantum Elite AI Coding System — Security & Identity Layer
#
# Decrypts a SOPS-encrypted file to stdout. NEVER writes plaintext to disk
# in CI environments. For local development, use --output to write to a file.
#
# Usage:
#   ./decrypt.sh <file-path>                    # Decrypt to stdout
#   ./decrypt.sh <file-path> --output <path>    # Decrypt to a file (local dev only)
#   ./decrypt.sh <file-path> --env              # Export as environment variables
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

# ───────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────

log() { echo "[decrypt] $*" >&2; }
error() { echo "[decrypt] ERROR: $*" >&2; }

# ───────────────────────────────────────────────────────────────────────
# Fetch Age private key from Vault (to temp file in RAM)
# ───────────────────────────────────────────────────────────────────────

setup_age_key() {
    # If SOPS_AGE_KEY_FILE is already set, use it
    if [ -n "${SOPS_AGE_KEY_FILE:-}" ] && [ -f "${SOPS_AGE_KEY_FILE}" ]; then
        return 0
    fi

    # If SOPS_AGE_KEY is set directly, use it
    if [ -n "${SOPS_AGE_KEY:-}" ]; then
        return 0
    fi

    if [ -z "$VAULT_TOKEN" ]; then
        error "VAULT_TOKEN must be set (or set SOPS_AGE_KEY / SOPS_AGE_KEY_FILE)"
        exit 1
    fi

    log "Fetching Age private key from Vault ..."

    local vault_response
    vault_response=$(curl -sf \
        -H "X-Vault-Token: ${VAULT_TOKEN}" \
        "${VAULT_ADDR}/v1/${VAULT_MOUNT}/data/${AGE_KEY_VAULT_PATH}" 2>/dev/null)

    if [ -z "$vault_response" ]; then
        error "Could not read Age key from Vault at ${AGE_KEY_VAULT_PATH}"
        exit 1
    fi

    # Extract private key
    local private_key
    private_key=$(echo "$vault_response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data['data']['data']['private_key'])
" 2>/dev/null)

    if [ -z "$private_key" ]; then
        error "Age private key not found in Vault response"
        exit 1
    fi

    # Write to a temp file in /dev/shm (tmpfs, RAM-only, never hits disk)
    # Falls back to mktemp if /dev/shm doesn't exist
    local key_dir="/dev/shm"
    if [ ! -d "$key_dir" ]; then
        key_dir="$(mktemp -d)"
        trap 'rm -rf "$key_dir"' EXIT
    fi

    export SOPS_AGE_KEY_FILE="${key_dir}/sops-age-key-$$"
    echo "$private_key" > "$SOPS_AGE_KEY_FILE"
    chmod 600 "$SOPS_AGE_KEY_FILE"

    # Ensure cleanup on exit
    trap 'rm -f "$SOPS_AGE_KEY_FILE" 2>/dev/null' EXIT INT TERM

    log "Age key loaded (in-memory tmpfs)"
}

# ───────────────────────────────────────────────────────────────────────
# Decrypt file
# ───────────────────────────────────────────────────────────────────────

decrypt_to_stdout() {
    local file="$1"

    if [ ! -f "$file" ]; then
        error "File not found: $file"
        exit 1
    fi

    # Check if file is actually SOPS-encrypted
    if ! grep -q '"sops"' "$file" 2>/dev/null && ! grep -q 'sops:' "$file" 2>/dev/null; then
        error "File does not appear to be SOPS-encrypted: $file"
        error "Outputting raw content (may not be encrypted)"
        cat "$file"
        return 0
    fi

    sops --config "$SOPS_CONFIG" --decrypt "$file"
}

decrypt_to_file() {
    local input="$1"
    local output="$2"

    # Safety check: prevent writing in CI
    if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${WOODPECKER:-}" ]; then
        error "Refusing to write plaintext to disk in CI environment"
        error "Use stdout mode instead: ./decrypt.sh $input | <command>"
        exit 1
    fi

    log "Decrypting $input -> $output"
    log "WARNING: Plaintext file created. Do not commit this file."

    sops --config "$SOPS_CONFIG" --decrypt "$input" > "$output"
    chmod 600 "$output"

    log "Decrypted: $output (permissions: 600)"
}

decrypt_as_env() {
    local file="$1"

    # Decrypt and convert to export statements
    local decrypted
    decrypted=$(decrypt_to_stdout "$file")

    echo "$decrypted" | while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        # Output as export statement
        echo "export $line"
    done
}

# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────

main() {
    if [ $# -lt 1 ]; then
        echo "Usage: $0 <file-path>                   # Decrypt to stdout" >&2
        echo "       $0 <file-path> --output <path>   # Decrypt to file (local dev)" >&2
        echo "       $0 <file-path> --env              # Export as env vars" >&2
        exit 1
    fi

    # Verify sops is installed
    if ! command -v sops &> /dev/null; then
        error "sops is not installed. Install from https://github.com/getsops/sops"
        exit 1
    fi

    local file="$1"
    shift

    setup_age_key

    if [ "${1:-}" = "--output" ]; then
        local output="${2:-}"
        if [ -z "$output" ]; then
            error "--output requires a file path"
            exit 1
        fi
        decrypt_to_file "$file" "$output"
    elif [ "${1:-}" = "--env" ]; then
        decrypt_as_env "$file"
    else
        decrypt_to_stdout "$file"
    fi
}

main "$@"
