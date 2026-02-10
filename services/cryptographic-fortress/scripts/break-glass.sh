#!/usr/bin/env bash
###############################################################################
# break-glass.sh - Emergency break-glass procedure for Vault
#
# System 2: Cryptographic Fortress
#
# Emergency procedure that:
# 1. Requires 3/5 unseal keys for authorization
# 2. Generates a time-limited root token (1h TTL)
# 3. Logs to audit trail and posts to Mattermost #security-alerts
# 4. Applies a full-access policy with automatic revocation
# 5. Auto-revokes after 1h
# 6. Triggers post-incident secret rotation for all accessed paths
###############################################################################
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
export VAULT_ADDR

MATTERMOST_WEBHOOK_URL="${MATTERMOST_WEBHOOK_URL:-}"
MATTERMOST_CHANNEL="${MATTERMOST_CHANNEL:-security-alerts}"
BREAK_GLASS_TTL="1h"
BREAK_GLASS_POLICY="break-glass-emergency"
KEY_THRESHOLD=3
KEY_SHARES=5
AUDIT_LOG="${BREAK_GLASS_AUDIT_LOG:-/vault/logs/break-glass-audit.log}"
INCIDENT_DIR="${INCIDENT_DIR:-/vault/incidents}"
ROTATION_SCRIPT="${ROTATION_SCRIPT:-$(cd "$(dirname "$0")" && pwd)/rotate-all-secrets.sh}"

# ---------------------------------------------------------------------------
# Colored timestamped output
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [ERROR]${NC} $*"; }
log_step()  { echo -e "${CYAN}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [STEP]${NC}  $*"; }
log_alert() { echo -e "${MAGENTA}[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [ALERT]${NC} $*"; }

# ---------------------------------------------------------------------------
# Cleanup trap
# ---------------------------------------------------------------------------
TEMP_FILES=()
ROOT_TOKEN=""
REVOCATION_PID=""

cleanup() {
    local exit_code=$?
    for f in "${TEMP_FILES[@]}"; do
        rm -f "$f" 2>/dev/null || true
    done
    if [[ -n "$REVOCATION_PID" ]]; then
        kill "$REVOCATION_PID" 2>/dev/null || true
    fi
    if [[ $exit_code -ne 0 ]]; then
        log_error "break-glass.sh exited with code $exit_code"
        audit_log "BREAK_GLASS_FAILED" "Script exited with code $exit_code"
    fi
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Audit logging (local file + syslog)
# ---------------------------------------------------------------------------
audit_log() {
    local event="$1"
    local details="${2:-}"
    local timestamp
    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    local caller="${BREAK_GLASS_OPERATOR:-$(whoami)}"
    local hostname
    hostname=$(hostname -f 2>/dev/null || hostname)

    local entry
    entry=$(python3 -c "
import json
print(json.dumps({
    'timestamp': '${timestamp}',
    'event': '${event}',
    'operator': '${caller}',
    'hostname': '${hostname}',
    'vault_addr': '${VAULT_ADDR}',
    'details': '''${details}'''
}))
" 2>/dev/null || echo "{\"timestamp\":\"${timestamp}\",\"event\":\"${event}\",\"details\":\"${details}\"}")

    mkdir -p "$(dirname "$AUDIT_LOG")" 2>/dev/null || true
    echo "$entry" >> "$AUDIT_LOG"
    logger -t "vault-break-glass" "$entry" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Post to Mattermost #security-alerts
# ---------------------------------------------------------------------------
post_mattermost_alert() {
    local message="$1"
    local urgency="${2:-high}"

    if [[ -z "$MATTERMOST_WEBHOOK_URL" ]]; then
        log_warn "MATTERMOST_WEBHOOK_URL not set -- skipping alert notification"
        return 0
    fi

    local icon=":rotating_light:"
    if [[ "$urgency" == "critical" ]]; then
        icon=":fire:"
    elif [[ "$urgency" == "resolved" ]]; then
        icon=":white_check_mark:"
    fi

    local payload
    payload=$(python3 -c "
import json
msg = '''${message}'''
print(json.dumps({
    'channel': '${MATTERMOST_CHANNEL}',
    'username': 'Vault Break-Glass',
    'icon_emoji': '${icon}',
    'text': f'${icon} **VAULT BREAK-GLASS PROCEDURE** ${icon}\n\n{msg}'
}))
" 2>/dev/null)

    if [[ -n "$payload" ]]; then
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "$MATTERMOST_WEBHOOK_URL" \
            --max-time 10 2>/dev/null || echo "000")

        if [[ "$http_code" == "200" ]]; then
            log_ok "Mattermost alert posted to #${MATTERMOST_CHANNEL}"
        else
            log_warn "Mattermost alert POST returned HTTP ${http_code}"
        fi
    fi
}

# ---------------------------------------------------------------------------
# Step 1: Collect unseal keys for authorization
# ---------------------------------------------------------------------------
collect_unseal_keys() {
    log_step "Step 1: Collect ${KEY_THRESHOLD}/${KEY_SHARES} Unseal Keys for Authorization"

    echo ""
    log_alert "=========================================="
    log_alert "  BREAK-GLASS EMERGENCY PROCEDURE"
    log_alert "=========================================="
    log_alert ""
    log_alert "This procedure will generate a ROOT TOKEN"
    log_alert "with FULL ACCESS to all Vault secrets."
    log_alert ""
    log_alert "Requirements:"
    log_alert "  - ${KEY_THRESHOLD} of ${KEY_SHARES} unseal key holders must participate"
    log_alert "  - All actions will be logged to audit trail"
    log_alert "  - Mattermost #security-alerts will be notified"
    log_alert "  - Token will auto-expire after ${BREAK_GLASS_TTL}"
    log_alert "  - Post-incident rotation will be triggered"
    log_alert ""
    log_alert "=========================================="
    echo ""

    # Collect operator identification
    if [[ -z "${BREAK_GLASS_OPERATOR:-}" ]]; then
        read -r -p "Enter your operator name/ID: " BREAK_GLASS_OPERATOR
    fi
    if [[ -z "${BREAK_GLASS_REASON:-}" ]]; then
        read -r -p "Enter reason for break-glass: " BREAK_GLASS_REASON
    fi

    audit_log "BREAK_GLASS_INITIATED" "operator=${BREAK_GLASS_OPERATOR}, reason=${BREAK_GLASS_REASON}"

    post_mattermost_alert "**Initiated by:** ${BREAK_GLASS_OPERATOR}\n**Reason:** ${BREAK_GLASS_REASON}\n**Time:** $(date -u '+%Y-%m-%dT%H:%M:%SZ')\n**Status:** Collecting unseal keys..." "critical"

    # Collect keys
    UNSEAL_KEYS=()
    local i=1
    while [[ ${#UNSEAL_KEYS[@]} -lt $KEY_THRESHOLD ]]; do
        echo ""
        read -r -s -p "Key holder ${i}: Enter unseal key (${#UNSEAL_KEYS[@]}/${KEY_THRESHOLD} collected): " key
        echo ""

        if [[ -z "$key" ]]; then
            log_warn "Empty key -- try again"
            continue
        fi

        # Validate the key format (base64, typically 44 chars)
        if [[ ${#key} -lt 20 ]]; then
            log_warn "Key appears too short -- try again"
            continue
        fi

        UNSEAL_KEYS+=("$key")
        log_ok "Key ${#UNSEAL_KEYS[@]}/${KEY_THRESHOLD} accepted"
        i=$((i + 1))
    done

    audit_log "UNSEAL_KEYS_COLLECTED" "count=${#UNSEAL_KEYS[@]}, threshold=${KEY_THRESHOLD}"
    log_ok "All ${KEY_THRESHOLD} unseal keys collected"
}

# ---------------------------------------------------------------------------
# Step 2: Generate root token
# ---------------------------------------------------------------------------
generate_root_token() {
    log_step "Step 2: Generate Emergency Root Token"

    # Initialize the root token generation
    log_info "Initializing root token generation..."
    local init_output
    init_output=$(vault operator generate-root -init -format=json 2>&1)

    local nonce
    nonce=$(echo "$init_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['nonce'])" 2>/dev/null)
    local otp
    otp=$(echo "$init_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['otp'])" 2>/dev/null)

    if [[ -z "$nonce" || -z "$otp" ]]; then
        log_error "Failed to initialize root token generation"
        audit_log "ROOT_TOKEN_INIT_FAILED" "Could not extract nonce/otp"
        return 1
    fi

    log_info "Root token generation initialized (nonce: ${nonce:0:8}...)"

    # Supply each unseal key
    local encoded_token=""
    local generation_complete="false"

    for i in "${!UNSEAL_KEYS[@]}"; do
        local key="${UNSEAL_KEYS[$i]}"
        local provide_output
        provide_output=$(vault operator generate-root \
            -nonce="$nonce" \
            -format=json \
            "$key" 2>&1)

        local complete
        complete=$(echo "$provide_output" | python3 -c "import sys,json; print(json.load(sys.stdin).get('complete', False))" 2>/dev/null)

        if [[ "$complete" == "True" ]]; then
            encoded_token=$(echo "$provide_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['encoded_root_token'])" 2>/dev/null)
            generation_complete="true"
            log_ok "Root token generation complete after key $((i + 1))"
            break
        else
            log_info "Key $((i + 1)) accepted, waiting for more keys..."
        fi
    done

    if [[ "$generation_complete" != "true" || -z "$encoded_token" ]]; then
        log_error "Root token generation did not complete"
        audit_log "ROOT_TOKEN_GENERATION_FAILED" "Did not reach threshold"
        return 1
    fi

    # Decode the root token using the OTP
    ROOT_TOKEN=$(vault operator generate-root -decode="$encoded_token" -otp="$otp" 2>/dev/null)

    if [[ -z "$ROOT_TOKEN" ]]; then
        log_error "Failed to decode root token"
        audit_log "ROOT_TOKEN_DECODE_FAILED" ""
        return 1
    fi

    audit_log "ROOT_TOKEN_GENERATED" "token_prefix=${ROOT_TOKEN:0:8}..."
    log_ok "Emergency root token generated (prefix: ${ROOT_TOKEN:0:8}...)"
}

# ---------------------------------------------------------------------------
# Step 3: Apply time-limited full-access policy
# ---------------------------------------------------------------------------
apply_emergency_policy() {
    log_step "Step 3: Apply Time-Limited Emergency Policy"

    export VAULT_TOKEN="$ROOT_TOKEN"

    # Create the break-glass policy with full access
    local policy_content
    policy_content=$(cat <<'EOHCL'
# Break-Glass Emergency Policy
# Auto-generated - full access for incident response
# This policy will be revoked after the TTL expires

path "*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}

path "sys/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}

path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
EOHCL
    )

    echo "$policy_content" | vault policy write "$BREAK_GLASS_POLICY" -
    log_ok "Emergency policy '${BREAK_GLASS_POLICY}' written"

    # Create a child token with TTL so it auto-expires
    local child_token_output
    child_token_output=$(vault token create \
        -policy="$BREAK_GLASS_POLICY" \
        -ttl="$BREAK_GLASS_TTL" \
        -display-name="break-glass-${BREAK_GLASS_OPERATOR}" \
        -metadata="operator=${BREAK_GLASS_OPERATOR}" \
        -metadata="reason=${BREAK_GLASS_REASON}" \
        -metadata="initiated=$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
        -format=json 2>&1)

    local emergency_token
    emergency_token=$(echo "$child_token_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['auth']['client_token'])" 2>/dev/null)
    local token_accessor
    token_accessor=$(echo "$child_token_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['auth']['accessor'])" 2>/dev/null)

    if [[ -z "$emergency_token" ]]; then
        log_error "Failed to create emergency child token"
        return 1
    fi

    # Store incident metadata
    mkdir -p "$INCIDENT_DIR" 2>/dev/null || true
    local incident_id
    incident_id="BG-$(date -u '+%Y%m%d-%H%M%S')-$(head -c 4 /dev/urandom | xxd -p)"
    local incident_file="${INCIDENT_DIR}/${incident_id}.json"

    python3 -c "
import json, sys
incident = {
    'incident_id': '${incident_id}',
    'operator': '${BREAK_GLASS_OPERATOR}',
    'reason': '${BREAK_GLASS_REASON}',
    'initiated': '$(date -u '+%Y-%m-%dT%H:%M:%SZ')',
    'token_accessor': '${token_accessor}',
    'ttl': '${BREAK_GLASS_TTL}',
    'root_token_prefix': '${ROOT_TOKEN:0:8}...',
    'emergency_token_prefix': '${emergency_token:0:8}...',
    'status': 'active'
}
with open('${incident_file}', 'w') as f:
    json.dump(incident, f, indent=2)
" 2>/dev/null

    audit_log "EMERGENCY_TOKEN_CREATED" "incident=${incident_id}, accessor=${token_accessor}, ttl=${BREAK_GLASS_TTL}"

    post_mattermost_alert "**Incident ID:** ${incident_id}\n**Operator:** ${BREAK_GLASS_OPERATOR}\n**Reason:** ${BREAK_GLASS_REASON}\n**Token TTL:** ${BREAK_GLASS_TTL}\n**Token Accessor:** ${token_accessor}\n**Status:** ACTIVE - Emergency access granted" "critical"

    echo ""
    log_alert "=========================================="
    log_alert "  EMERGENCY ACCESS GRANTED"
    log_alert "=========================================="
    log_alert ""
    log_alert "  Incident ID : ${incident_id}"
    log_alert "  Token       : ${emergency_token}"
    log_alert "  Accessor    : ${token_accessor}"
    log_alert "  Expires     : ${BREAK_GLASS_TTL} from now"
    log_alert ""
    log_alert "  Usage: export VAULT_TOKEN=${emergency_token}"
    log_alert ""
    log_alert "  WARNING: All actions are audited."
    log_alert "  Token will auto-revoke after ${BREAK_GLASS_TTL}."
    log_alert "=========================================="
    echo ""

    EMERGENCY_TOKEN="$emergency_token"
    EMERGENCY_ACCESSOR="$token_accessor"
    INCIDENT_ID="$incident_id"
    INCIDENT_FILE="$incident_file"
}

# ---------------------------------------------------------------------------
# Step 4: Schedule auto-revocation
# ---------------------------------------------------------------------------
schedule_auto_revocation() {
    log_step "Step 4: Schedule Auto-Revocation"

    # Convert TTL to seconds
    local ttl_seconds
    ttl_seconds=$(python3 -c "
ttl = '${BREAK_GLASS_TTL}'
if ttl.endswith('h'):
    print(int(ttl[:-1]) * 3600)
elif ttl.endswith('m'):
    print(int(ttl[:-1]) * 60)
elif ttl.endswith('s'):
    print(int(ttl[:-1]))
else:
    print(3600)
" 2>/dev/null)

    log_info "Auto-revocation scheduled in ${ttl_seconds}s (${BREAK_GLASS_TTL})"

    # Launch background revocation process
    (
        sleep "$ttl_seconds"

        # Revoke the emergency token
        VAULT_TOKEN="$ROOT_TOKEN" vault token revoke -accessor "$EMERGENCY_ACCESSOR" 2>/dev/null || true

        # Clean up the break-glass policy
        VAULT_TOKEN="$ROOT_TOKEN" vault policy delete "$BREAK_GLASS_POLICY" 2>/dev/null || true

        # Revoke the root token itself
        VAULT_TOKEN="$ROOT_TOKEN" vault token revoke -self 2>/dev/null || true

        # Update incident file
        if [[ -f "$INCIDENT_FILE" ]]; then
            python3 -c "
import json
with open('${INCIDENT_FILE}', 'r') as f:
    incident = json.load(f)
incident['status'] = 'revoked'
incident['revoked_at'] = '$(date -u '+%Y-%m-%dT%H:%M:%SZ')'
with open('${INCIDENT_FILE}', 'w') as f:
    json.dump(incident, f, indent=2)
" 2>/dev/null || true
        fi

        # Log revocation
        audit_log "EMERGENCY_TOKEN_REVOKED" "incident=${INCIDENT_ID}, auto_revocation=true"

        # Notify Mattermost
        post_mattermost_alert "**Incident ID:** ${INCIDENT_ID}\n**Status:** REVOKED - Emergency access has been automatically revoked\n**Time:** $(date -u '+%Y-%m-%dT%H:%M:%SZ')\n**Next Step:** Post-incident secret rotation triggered" "resolved"

        # Trigger post-incident rotation
        trigger_post_incident_rotation

    ) &
    REVOCATION_PID=$!
    disown "$REVOCATION_PID" 2>/dev/null || true

    log_ok "Auto-revocation background process started (PID: ${REVOCATION_PID})"
}

# ---------------------------------------------------------------------------
# Step 5: Post-incident rotation
# ---------------------------------------------------------------------------
trigger_post_incident_rotation() {
    log_step "Step 5: Post-Incident Secret Rotation"

    audit_log "POST_INCIDENT_ROTATION_STARTED" "incident=${INCIDENT_ID}"

    # Read the Vault audit log to identify accessed secrets during the incident window
    local accessed_paths=()

    if [[ -f "/vault/logs/audit.log" ]]; then
        local incident_start
        incident_start=$(python3 -c "
import json
with open('${INCIDENT_FILE}', 'r') as f:
    print(json.load(f)['initiated'])
" 2>/dev/null || echo "")

        if [[ -n "$incident_start" ]]; then
            # Extract paths accessed with the emergency token accessor
            while IFS= read -r line; do
                local path
                path=$(echo "$line" | python3 -c "
import sys, json
try:
    entry = json.load(sys.stdin)
    req = entry.get('request', {})
    if req.get('client_token_accessor') == '${EMERGENCY_ACCESSOR}':
        path = req.get('path', '')
        if path and path.startswith('secret/'):
            print(path)
except:
    pass
" 2>/dev/null)
                if [[ -n "$path" ]]; then
                    accessed_paths+=("$path")
                fi
            done < "/vault/logs/audit.log"
        fi
    fi

    if [[ ${#accessed_paths[@]} -gt 0 ]]; then
        log_warn "Secrets accessed during incident (rotation required):"
        local unique_paths
        unique_paths=$(printf '%s\n' "${accessed_paths[@]}" | sort -u)
        while IFS= read -r path; do
            log_warn "  - ${path}"
        done <<< "$unique_paths"

        audit_log "SECRETS_ACCESSED_DURING_INCIDENT" "paths=$(printf '%s,' "${accessed_paths[@]}")"
    else
        log_info "No secret paths identified in audit log for rotation"
    fi

    # Trigger the rotation script if available
    if [[ -x "$ROTATION_SCRIPT" ]]; then
        log_info "Running rotation script: ${ROTATION_SCRIPT}"
        "$ROTATION_SCRIPT" --incident-id="${INCIDENT_ID}" --paths="${accessed_paths[*]:-all}" 2>&1 || {
            log_warn "Rotation script exited with errors"
        }
    else
        log_warn "Rotation script not found at ${ROTATION_SCRIPT}"
        log_warn "Manual rotation required for all secrets accessed during incident ${INCIDENT_ID}"

        post_mattermost_alert "**Incident ID:** ${INCIDENT_ID}\n**ACTION REQUIRED:** Manual secret rotation needed.\n**Accessed paths during incident:** ${#accessed_paths[@]} secrets\n**Rotation script not found.** Please rotate manually." "critical"
    fi

    audit_log "POST_INCIDENT_ROTATION_COMPLETE" "incident=${INCIDENT_ID}"
}

# ---------------------------------------------------------------------------
# Manual revocation (can be called separately)
# ---------------------------------------------------------------------------
revoke_emergency_access() {
    local accessor="${1:?Usage: revoke_emergency_access <token-accessor>}"

    log_step "Manual Revocation: accessor=${accessor}"

    if [[ -z "${VAULT_TOKEN:-}" ]]; then
        log_error "VAULT_TOKEN not set. Need privileged token to revoke."
        return 1
    fi

    vault token revoke -accessor "$accessor"
    vault policy delete "$BREAK_GLASS_POLICY" 2>/dev/null || true

    audit_log "EMERGENCY_TOKEN_MANUAL_REVOKE" "accessor=${accessor}"
    post_mattermost_alert "**Manual Revocation:** Token accessor ${accessor} has been revoked\n**Operator:** $(whoami)\n**Time:** $(date -u '+%Y-%m-%dT%H:%M:%SZ')" "resolved"

    log_ok "Emergency token revoked: ${accessor}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo ""
    echo -e "${RED}======================================================================"
    echo " VAULT BREAK-GLASS EMERGENCY PROCEDURE"
    echo " Vault Address: ${VAULT_ADDR}"
    echo " Date: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo -e "======================================================================${NC}"
    echo ""

    # Handle subcommands
    case "${1:-run}" in
        run)
            collect_unseal_keys
            generate_root_token
            apply_emergency_policy
            schedule_auto_revocation

            echo ""
            log_ok "Break-glass procedure complete. Emergency access is active."
            log_warn "Token will auto-revoke in ${BREAK_GLASS_TTL}."
            log_warn "All actions are being audited."
            echo ""
            ;;
        revoke)
            revoke_emergency_access "${2:-}"
            ;;
        status)
            log_info "Checking active break-glass incidents..."
            if [[ -d "$INCIDENT_DIR" ]]; then
                local active=0
                for f in "$INCIDENT_DIR"/*.json; do
                    [[ -f "$f" ]] || continue
                    local status
                    status=$(python3 -c "import json; print(json.load(open('$f'))['status'])" 2>/dev/null || echo "unknown")
                    local id
                    id=$(python3 -c "import json; print(json.load(open('$f'))['incident_id'])" 2>/dev/null || echo "unknown")
                    local operator
                    operator=$(python3 -c "import json; print(json.load(open('$f'))['operator'])" 2>/dev/null || echo "unknown")
                    echo "  ${id}: status=${status}, operator=${operator}"
                    if [[ "$status" == "active" ]]; then
                        active=$((active + 1))
                    fi
                done
                log_info "Active incidents: ${active}"
            else
                log_info "No incident directory found"
            fi
            ;;
        *)
            echo "Usage: $0 {run|revoke <accessor>|status}"
            exit 1
            ;;
    esac
}

main "$@"
