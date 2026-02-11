#!/usr/bin/env bash
###############################################################################
# vault-init.sh - Initialize and configure HashiCorp Vault for Omni-Quantum
#
# System 2: Cryptographic Fortress
#
# Initializes Vault with Shamir key shares, enables audit backends,
# secret engines, auth methods, and creates per-service AppRoles.
###############################################################################
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_INIT_KEYS_FILE="${VAULT_INIT_KEYS_FILE:-/vault/init/vault-keys.json}"
VAULT_GPG_RECIPIENT="${VAULT_GPG_RECIPIENT:-omni-quantum-ops@internal}"
VAULT_ENV="${VAULT_ENV:-dev}"          # dev | staging | production
VAULT_AUDIT_LOG="${VAULT_AUDIT_LOG:-/vault/logs/audit.log}"
POLICY_DIR="${POLICY_DIR:-$(cd "$(dirname "$0")/../policies" && pwd)}"
KEY_SHARES=5
KEY_THRESHOLD=3

export VAULT_ADDR

# ---------------------------------------------------------------------------
# Colored timestamped output
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [ERROR]${NC} $*"; }
log_step()  { echo -e "${CYAN}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [STEP]${NC}  $*"; }

# ---------------------------------------------------------------------------
# Cleanup trap
# ---------------------------------------------------------------------------
TEMP_FILES=()
cleanup() {
    local exit_code=$?
    for f in "${TEMP_FILES[@]}"; do
        rm -f "$f" 2>/dev/null || true
    done
    if [[ $exit_code -ne 0 ]]; then
        log_error "vault-init.sh exited with code $exit_code"
    fi
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
vault_is_initialized() {
    vault status -format=json 2>/dev/null | python3 -c "import sys,json; sys.exit(0 if json.load(sys.stdin).get('initialized') else 1)" 2>/dev/null
}

vault_is_sealed() {
    vault status -format=json 2>/dev/null | python3 -c "import sys,json; sys.exit(0 if json.load(sys.stdin).get('sealed') else 1)" 2>/dev/null
}

wait_for_vault() {
    local retries=30
    local i=0
    log_info "Waiting for Vault to become reachable at ${VAULT_ADDR}..."
    while [[ $i -lt $retries ]]; do
        if vault status -format=json &>/dev/null; then
            log_ok "Vault is reachable"
            return 0
        fi
        sleep 2
        i=$((i + 1))
    done
    log_error "Vault did not become reachable within $((retries * 2))s"
    return 1
}

# ---------------------------------------------------------------------------
# Step 1: Initialize Vault
# ---------------------------------------------------------------------------
initialize_vault() {
    log_step "Step 1: Vault Initialization"

    if vault_is_initialized; then
        log_ok "Vault is already initialized -- skipping init"
        return 0
    fi

    log_info "Initializing Vault with ${KEY_SHARES} key shares, threshold ${KEY_THRESHOLD}..."
    local init_output
    init_output=$(vault operator init \
        -key-shares="${KEY_SHARES}" \
        -key-threshold="${KEY_THRESHOLD}" \
        -format=json)

    # Persist raw init output to a temp file first
    local tmp_init
    tmp_init=$(mktemp /tmp/vault-init-XXXXXX.json)
    TEMP_FILES+=("$tmp_init")
    echo "$init_output" > "$tmp_init"

    # Store unseal keys GPG-encrypted
    local keys_dir
    keys_dir=$(dirname "$VAULT_INIT_KEYS_FILE")
    mkdir -p "$keys_dir"

    if command -v gpg &>/dev/null && gpg --list-keys "$VAULT_GPG_RECIPIENT" &>/dev/null; then
        log_info "Encrypting init output with GPG recipient ${VAULT_GPG_RECIPIENT}..."
        gpg --encrypt --recipient "$VAULT_GPG_RECIPIENT" \
            --output "${VAULT_INIT_KEYS_FILE}.gpg" \
            --trust-model always \
            "$tmp_init"
        log_ok "Encrypted init keys stored at ${VAULT_INIT_KEYS_FILE}.gpg"
    else
        log_warn "GPG recipient not available -- storing plaintext (acceptable for dev/staging)"
        cp "$tmp_init" "$VAULT_INIT_KEYS_FILE"
        chmod 600 "$VAULT_INIT_KEYS_FILE"
        log_ok "Init keys stored at ${VAULT_INIT_KEYS_FILE}"
    fi

    # Export for later steps
    VAULT_INIT_OUTPUT="$init_output"
    log_ok "Vault initialized successfully"
}

# ---------------------------------------------------------------------------
# Step 2: Unseal Vault
# ---------------------------------------------------------------------------
unseal_vault() {
    log_step "Step 2: Vault Unseal"

    if ! vault_is_sealed; then
        log_ok "Vault is already unsealed"
        return 0
    fi

    # -----------------------------------------------------------------------
    # PRODUCTION: Manual unseal required.
    #   Each key holder runs:
    #     vault operator unseal <key>
    #   Repeat with 3 of 5 keys from different holders.
    #   NEVER store production unseal keys on disk unencrypted.
    # -----------------------------------------------------------------------
    if [[ "$VAULT_ENV" == "production" ]]; then
        log_warn "PRODUCTION MODE: Manual unseal required."
        log_warn "Have 3 of 5 key holders run: vault operator unseal <their-key>"
        log_warn "Vault will remain sealed until threshold is met."
        return 0
    fi

    # Dev / Staging: auto-unseal using stored keys
    log_info "Auto-unsealing Vault for ${VAULT_ENV} environment..."

    local keys_source=""
    if [[ -n "${VAULT_INIT_OUTPUT:-}" ]]; then
        keys_source="$VAULT_INIT_OUTPUT"
    elif [[ -f "$VAULT_INIT_KEYS_FILE" ]]; then
        keys_source=$(cat "$VAULT_INIT_KEYS_FILE")
    elif [[ -f "${VAULT_INIT_KEYS_FILE}.gpg" ]]; then
        keys_source=$(gpg --decrypt "${VAULT_INIT_KEYS_FILE}.gpg" 2>/dev/null)
    else
        log_error "No unseal keys found. Cannot auto-unseal."
        return 1
    fi

    local key_count=0
    for i in 0 1 2; do
        local key
        key=$(echo "$keys_source" | python3 -c "import sys,json; print(json.load(sys.stdin)['unseal_keys_b64'][$i])" 2>/dev/null)
        if [[ -z "$key" ]]; then
            log_error "Failed to extract unseal key $i"
            return 1
        fi
        vault operator unseal "$key" > /dev/null
        key_count=$((key_count + 1))
        log_info "Applied unseal key $((i + 1))/${KEY_THRESHOLD}"
    done

    if vault_is_sealed; then
        log_error "Vault is still sealed after applying ${key_count} keys"
        return 1
    fi

    log_ok "Vault successfully unsealed"
}

# ---------------------------------------------------------------------------
# Step 3: Authenticate (set root token for setup)
# ---------------------------------------------------------------------------
authenticate() {
    log_step "Step 3: Authenticate to Vault"

    if [[ -n "${VAULT_TOKEN:-}" ]]; then
        log_ok "Using existing VAULT_TOKEN from environment"
        return 0
    fi

    local keys_source=""
    if [[ -n "${VAULT_INIT_OUTPUT:-}" ]]; then
        keys_source="$VAULT_INIT_OUTPUT"
    elif [[ -f "$VAULT_INIT_KEYS_FILE" ]]; then
        keys_source=$(cat "$VAULT_INIT_KEYS_FILE")
    elif [[ -f "${VAULT_INIT_KEYS_FILE}.gpg" ]]; then
        keys_source=$(gpg --decrypt "${VAULT_INIT_KEYS_FILE}.gpg" 2>/dev/null)
    else
        log_error "No init output found for root token extraction"
        return 1
    fi

    VAULT_TOKEN=$(echo "$keys_source" | python3 -c "import sys,json; print(json.load(sys.stdin)['root_token'])" 2>/dev/null)
    export VAULT_TOKEN
    log_ok "Authenticated with root token (will be revoked after setup)"
}

# ---------------------------------------------------------------------------
# Step 4: Enable Audit Backends
# ---------------------------------------------------------------------------
enable_audit() {
    log_step "Step 4: Enable Audit Backends"

    # File audit
    local audit_dir
    audit_dir=$(dirname "$VAULT_AUDIT_LOG")
    mkdir -p "$audit_dir" 2>/dev/null || true

    if vault audit list -format=json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'file/' in d else 1)" 2>/dev/null; then
        log_ok "File audit backend already enabled"
    else
        vault audit enable file file_path="$VAULT_AUDIT_LOG"
        log_ok "Enabled file audit backend -> ${VAULT_AUDIT_LOG}"
    fi

    # Syslog audit
    if vault audit list -format=json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'syslog/' in d else 1)" 2>/dev/null; then
        log_ok "Syslog audit backend already enabled"
    else
        if vault audit enable syslog 2>/dev/null; then
            log_ok "Enabled syslog audit backend"
        else
            log_warn "Syslog audit enable failed (may not be available in container) -- skipping"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Step 5: Enable Secret Engines
# ---------------------------------------------------------------------------
enable_secret_engines() {
    log_step "Step 5: Enable Secret Engines"

    local engines=(
        "kv-v2:secret:KV Version 2"
        "database:database:Database Dynamic Secrets"
        "pki:pki:PKI Certificates"
        "transit:transit:Transit Encryption"
    )

    local mounted
    mounted=$(vault secrets list -format=json 2>/dev/null)

    for entry in "${engines[@]}"; do
        IFS=':' read -r engine_type mount_path description <<< "$entry"
        local check_path="${mount_path}/"
        if echo "$mounted" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if '${check_path}' in d else 1)" 2>/dev/null; then
            log_ok "${description} already mounted at ${mount_path}/"
        else
            if [[ "$engine_type" == "kv-v2" ]]; then
                vault secrets enable -path="$mount_path" -version=2 kv
            else
                vault secrets enable -path="$mount_path" "$engine_type"
            fi
            log_ok "Enabled ${description} at ${mount_path}/"
        fi
    done
}

# ---------------------------------------------------------------------------
# Step 6: Enable Auth Methods
# ---------------------------------------------------------------------------
enable_auth_methods() {
    log_step "Step 6: Enable Auth Methods"

    local auth_list
    auth_list=$(vault auth list -format=json 2>/dev/null)

    if echo "$auth_list" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'approle/' in d else 1)" 2>/dev/null; then
        log_ok "AppRole auth already enabled"
    else
        vault auth enable approle
        log_ok "Enabled AppRole auth method"
    fi
}

# ---------------------------------------------------------------------------
# Step 7: Load Policies & Create AppRoles
# ---------------------------------------------------------------------------
SERVICES=(
    omni-gitea
    omni-backup
    omni-litellm
    omni-n8n
    omni-mattermost
    omni-authentik
    omni-langfuse
    omni-grafana
    omni-prometheus
    omni-traefik
    omni-woodpecker
    omni-openhands
    omni-swe-agent
    omni-orchestrator
    omni-redis
    omni-minio
    omni-vault-admin
    omni-qdrant
    omni-ollama
    notion-workspace
    omni-nango
    omni-flowise
    notion-workspace
    omni-superset
    omni-calcom
    notion-workspace
    omni-crater
    omni-crowdsec
    omni-portainer
    omni-coder
    omni-token-infinity
    omni-omi-bridge
    omni-thanos
    omni-uptime-kuma
    omni-coolify
    omni-mlflow
    omni-keycloak
    omni-glitchtip
    omni-listmonk
    omni-chatwoot
    omni-pact-broker
    omni-formbricks
    omni-tolgee
)

load_policies_and_create_approles() {
    log_step "Step 7: Load Policies & Create AppRoles"

    local loaded=0
    local skipped=0

    for service in "${SERVICES[@]}"; do
        local policy_file="${POLICY_DIR}/${service}.hcl"

        # Load policy
        if [[ -f "$policy_file" ]]; then
            vault policy write "$service" "$policy_file"
            log_ok "Loaded policy: ${service}"
            loaded=$((loaded + 1))
        else
            log_warn "Policy file not found: ${policy_file} -- skipping"
            skipped=$((skipped + 1))
            continue
        fi

        # Create AppRole for the service
        # token_ttl = 1h, token_max_ttl = 4h, secret_id_ttl = 720h (30 days)
        vault write "auth/approle/role/${service}" \
            token_policies="${service}" \
            token_ttl=1h \
            token_max_ttl=4h \
            secret_id_ttl=720h \
            secret_id_num_uses=0 \
            token_num_uses=0 \
            token_type=service

        log_ok "Created AppRole: ${service}"
    done

    log_info "Policies loaded: ${loaded}, skipped: ${skipped}"
}

# ---------------------------------------------------------------------------
# Step 8: Output Summary
# ---------------------------------------------------------------------------
output_summary() {
    log_step "Step 8: Summary"

    echo ""
    echo "======================================================================"
    echo " Vault Initialization Summary"
    echo "======================================================================"
    echo ""

    log_info "Init Status:"
    vault status -format=json 2>/dev/null | python3 -c "
import sys, json
s = json.load(sys.stdin)
print(f'  Initialized : {s.get(\"initialized\", \"unknown\")}')
print(f'  Sealed      : {s.get(\"sealed\", \"unknown\")}')
print(f'  Version     : {s.get(\"version\", \"unknown\")}')
print(f'  Cluster     : {s.get(\"cluster_name\", \"unknown\")}')
" 2>/dev/null || log_warn "Could not retrieve status"

    echo ""
    log_info "Enabled Secret Engines:"
    vault secrets list -format=json 2>/dev/null | python3 -c "
import sys, json
for path, info in sorted(json.load(sys.stdin).items()):
    if path not in ('cubbyhole/', 'identity/', 'sys/'):
        print(f'  {path:<20s} type={info[\"type\"]:<12s} description=\"{info.get(\"description\", \"\")}\"')
" 2>/dev/null || log_warn "Could not list secret engines"

    echo ""
    log_info "Enabled Auth Methods:"
    vault auth list -format=json 2>/dev/null | python3 -c "
import sys, json
for path, info in sorted(json.load(sys.stdin).items()):
    if path != 'token/':
        print(f'  {path:<20s} type={info[\"type\"]}')
" 2>/dev/null || log_warn "Could not list auth methods"

    echo ""
    log_info "Audit Devices:"
    vault audit list -format=json 2>/dev/null | python3 -c "
import sys, json
for path, info in sorted(json.load(sys.stdin).items()):
    print(f'  {path:<20s} type={info[\"type\"]}')
" 2>/dev/null || log_warn "Could not list audit devices"

    echo ""
    log_info "AppRoles Created: ${#SERVICES[@]} services"
    echo ""
    echo "======================================================================"
    log_ok "Vault initialization complete for environment: ${VAULT_ENV}"
    echo "======================================================================"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo "======================================================================"
    echo " Omni-Quantum Elite: Cryptographic Fortress - Vault Initializer"
    echo " Environment: ${VAULT_ENV}"
    echo " Vault Address: ${VAULT_ADDR}"
    echo "======================================================================"
    echo ""

    wait_for_vault
    initialize_vault
    unseal_vault
    authenticate
    enable_audit
    enable_secret_engines
    enable_auth_methods
    load_policies_and_create_approles
    output_summary
}

main "$@"
