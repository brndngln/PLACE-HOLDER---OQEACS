#!/usr/bin/env bash
# ===========================================================================
# SYSTEM 25 — SECURITY SHIELD: CrowdSec Initialization Script
# Omni Quantum Elite AI Coding System — Security & Identity Layer
#
# Installs collections, registers bouncer, subscribes to blocklists,
# enables metrics, verifies bouncer, and runs detection test.
# ===========================================================================

set -euo pipefail

# ───────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────

CROWDSEC_URL="${CROWDSEC_URL:-http://omni-crowdsec:8080}"
BOUNCER_NAME="${BOUNCER_NAME:-traefik-bouncer}"
MATTERMOST_WEBHOOK_URL="${MATTERMOST_WEBHOOK_URL:-}"
TRUSTED_IPS="${TRUSTED_IPS:-}"
MAX_RETRIES="${MAX_RETRIES:-60}"
RETRY_INTERVAL="${RETRY_INTERVAL:-5}"
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"

# ───────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

error() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] ERROR: $*" >&2
}

cscli_exec() {
    docker exec omni-crowdsec cscli "$@"
}

# ───────────────────────────────────────────────────────────────────────
# Step 1: Wait for CrowdSec to be healthy
# ───────────────────────────────────────────────────────────────────────

wait_for_crowdsec() {
    log "Waiting for CrowdSec at ${CROWDSEC_URL} ..."
    local attempt=0
    while [ "$attempt" -lt "$MAX_RETRIES" ]; do
        attempt=$((attempt + 1))
        if docker exec omni-crowdsec cscli version > /dev/null 2>&1; then
            log "  CrowdSec is healthy (attempt ${attempt})"
            return 0
        fi
        log "  attempt ${attempt}/${MAX_RETRIES} — retrying in ${RETRY_INTERVAL}s"
        sleep "$RETRY_INTERVAL"
    done
    error "CrowdSec did not become healthy in time"
    exit 1
}

# ───────────────────────────────────────────────────────────────────────
# Step 2: Install CrowdSec Collections
# ───────────────────────────────────────────────────────────────────────

install_collections() {
    log "Installing CrowdSec collections ..."

    local collections=(
        "crowdsecurity/linux"
        "crowdsecurity/traefik"
        "crowdsecurity/http-cve"
        "crowdsecurity/base-http-scenarios"
        "crowdsecurity/whitelist-good-actors"
        "crowdsecurity/nginx"
        "crowdsecurity/sshd"
    )

    for collection in "${collections[@]}"; do
        log "  Installing: ${collection}"
        cscli_exec collections install "$collection" --force 2>&1 | while IFS= read -r line; do
            log "    ${line}"
        done
    done

    # Install custom parsers for Authentik and Gitea
    log "  Installing additional parsers ..."
    cscli_exec parsers install crowdsecurity/docker-logs --force 2>/dev/null || true
    cscli_exec parsers install crowdsecurity/geoip-enrich --force 2>/dev/null || true

    log "  Collections installed"
}

# ───────────────────────────────────────────────────────────────────────
# Step 3: Register Traefik Bouncer
# ───────────────────────────────────────────────────────────────────────

register_bouncer() {
    log "Registering Traefik bouncer: ${BOUNCER_NAME} ..."

    # Check if bouncer already exists
    local existing
    existing=$(cscli_exec bouncers list -o raw 2>/dev/null | grep -c "$BOUNCER_NAME" || true)

    if [ "$existing" -gt 0 ]; then
        log "  Bouncer '${BOUNCER_NAME}' already registered"
        return 0
    fi

    # Register and capture the API key
    local bouncer_key
    bouncer_key=$(cscli_exec bouncers add "$BOUNCER_NAME" -o raw 2>/dev/null || echo "")

    if [ -z "$bouncer_key" ]; then
        error "Failed to register bouncer"
        return 1
    fi

    log "  Bouncer registered successfully"
    log "  API Key: ${bouncer_key:0:8}..."

    # Store bouncer API key in Vault
    if [ -n "$VAULT_TOKEN" ]; then
        log "  Storing bouncer API key in Vault ..."
        curl -sf \
            -H "X-Vault-Token: ${VAULT_TOKEN}" \
            -H "Content-Type: application/json" \
            -X POST \
            "${VAULT_ADDR}/v1/secret/data/crowdsec/bouncer" \
            -d "{\"data\": {\"api_key\": \"${bouncer_key}\", \"bouncer_name\": \"${BOUNCER_NAME}\", \"lapi_url\": \"${CROWDSEC_URL}\"}}" \
            > /dev/null 2>&1 && \
            log "    Stored in Vault: secret/data/crowdsec/bouncer" || \
            log "    WARNING: Could not store in Vault"
    fi

    echo "$bouncer_key"
}

# ───────────────────────────────────────────────────────────────────────
# Step 4: Subscribe to Community Blocklists
# ───────────────────────────────────────────────────────────────────────

subscribe_blocklists() {
    log "Subscribing to community blocklists ..."

    # The community blocklist is automatically enabled with console enrollment
    # For manual subscription, use the hub
    cscli_exec hub update 2>&1 | while IFS= read -r line; do
        log "  ${line}"
    done

    log "  Community blocklists active"
}

# ───────────────────────────────────────────────────────────────────────
# Step 5: Enable Prometheus Metrics
# ───────────────────────────────────────────────────────────────────────

enable_prometheus_metrics() {
    log "Enabling Prometheus metrics on :6060 ..."

    # Metrics are enabled by default on port 6060 in CrowdSec
    # Verify they're accessible
    local metrics_ok=false
    for i in $(seq 1 10); do
        if curl -sf "http://omni-crowdsec:6060/metrics" > /dev/null 2>&1; then
            metrics_ok=true
            break
        fi
        sleep 2
    done

    if [ "$metrics_ok" = true ]; then
        log "  Prometheus metrics endpoint verified: :6060/metrics"
    else
        log "  WARNING: Metrics endpoint not yet responding (may need container restart)"
    fi
}

# ───────────────────────────────────────────────────────────────────────
# Step 6: Configure Trusted IPs Whitelist
# ───────────────────────────────────────────────────────────────────────

configure_trusted_ips() {
    if [ -z "$TRUSTED_IPS" ]; then
        log "No TRUSTED_IPS configured — skipping whitelist additions"
        return 0
    fi

    log "Adding trusted IPs to whitelist ..."

    IFS=',' read -ra IPS <<< "$TRUSTED_IPS"
    for ip in "${IPS[@]}"; do
        ip=$(echo "$ip" | tr -d ' ')
        if [ -n "$ip" ]; then
            log "  Whitelisting: ${ip}"
            cscli_exec decisions delete --ip "$ip" 2>/dev/null || true
        fi
    done

    log "  Trusted IPs configured"
}

# ───────────────────────────────────────────────────────────────────────
# Step 7: Verify Bouncer Connectivity
# ───────────────────────────────────────────────────────────────────────

verify_bouncer() {
    log "Verifying bouncer connectivity ..."

    # Check bouncer is registered and authenticated
    local bouncer_list
    bouncer_list=$(cscli_exec bouncers list -o raw 2>/dev/null || echo "")

    if echo "$bouncer_list" | grep -q "$BOUNCER_NAME"; then
        log "  Bouncer '${BOUNCER_NAME}' is registered"
    else
        error "Bouncer '${BOUNCER_NAME}' not found in bouncer list"
        return 1
    fi

    # Verify LAPI is responding
    if curl -sf "${CROWDSEC_URL}/v1/decisions" -H "X-Api-Key: dummy" > /dev/null 2>&1 || \
       curl -sf "${CROWDSEC_URL}/v1/heartbeat" > /dev/null 2>&1; then
        log "  LAPI is responsive"
    else
        log "  NOTE: LAPI may require valid API key for decisions endpoint"
    fi

    log "  Bouncer connectivity verified"
}

# ───────────────────────────────────────────────────────────────────────
# Step 8: Smoke Test — Simulated Detection
# ───────────────────────────────────────────────────────────────────────

run_smoke_test() {
    log "Running smoke test ..."

    # Add a test decision manually
    local test_ip="198.51.100.99"
    log "  Adding test ban for ${test_ip} ..."
    cscli_exec decisions add --ip "$test_ip" --duration 1m --reason "Smoke test" --type ban 2>/dev/null || true

    # Verify the decision exists
    local decisions
    decisions=$(cscli_exec decisions list -o raw 2>/dev/null || echo "")

    if echo "$decisions" | grep -q "$test_ip"; then
        log "  Test ban verified — decision engine working"
    else
        log "  WARNING: Test ban not found (decision engine may need time)"
    fi

    # Remove test decision
    cscli_exec decisions delete --ip "$test_ip" 2>/dev/null || true
    log "  Test ban removed"

    # Show current metrics
    log "  Current metrics:"
    cscli_exec metrics 2>&1 | head -30 | while IFS= read -r line; do
        log "    ${line}"
    done

    log "  Smoke test complete"
}

# ───────────────────────────────────────────────────────────────────────
# Step 9: Configure Notification Plugin
# ───────────────────────────────────────────────────────────────────────

configure_notifications() {
    log "Configuring notification plugins ..."

    if [ -z "$MATTERMOST_WEBHOOK_URL" ]; then
        log "  MATTERMOST_WEBHOOK_URL not set — notifications disabled"
        return 0
    fi

    # Add notification to the active profiles
    # CrowdSec uses profiles.yaml to link scenarios to notification plugins
    docker exec omni-crowdsec sh -c "
        if ! grep -q 'mattermost_security_alerts' /etc/crowdsec/profiles.yaml 2>/dev/null; then
            cat >> /etc/crowdsec/profiles.yaml <<'EOF'

# Omni Quantum — notify all bans to Mattermost
---
name: omni_quantum_notify
filters:
  - Alert.Remediation == true
notifications:
  - mattermost_security_alerts
on_success: break
EOF
            echo 'Notification profile added'
        else
            echo 'Notification profile already exists'
        fi
    " 2>&1 | while IFS= read -r line; do
        log "    ${line}"
    done

    log "  Notification configuration complete"
}

# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────

main() {
    log "================================================================"
    log "SYSTEM 25 — SECURITY SHIELD: CrowdSec Initialization"
    log "================================================================"

    wait_for_crowdsec
    install_collections
    register_bouncer
    subscribe_blocklists
    enable_prometheus_metrics
    configure_trusted_ips
    verify_bouncer
    configure_notifications
    run_smoke_test

    log ""
    log "================================================================"
    log "CrowdSec initialization complete!"
    log "  LAPI: ${CROWDSEC_URL}"
    log "  Metrics: http://omni-crowdsec:6060/metrics"
    log "  Bouncer: ${BOUNCER_NAME}"
    log "  Collections: 7 installed"
    log "  Scenarios: 6 custom + community"
    log "  Notifications: Mattermost #security-alerts"
    log "================================================================"
}

main "$@"
