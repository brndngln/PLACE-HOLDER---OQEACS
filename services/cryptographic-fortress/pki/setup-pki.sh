#!/usr/bin/env bash
###############################################################################
# setup-pki.sh - Configure PKI secret engine with Root & Intermediate CAs
#
# System 2: Cryptographic Fortress
#
# Creates a Root CA (10yr, offline storage), Intermediate CA (2yr), and
# an internal role for issuing service certificates (EC P-256, 72h max TTL).
# Includes an issue-cert function for generating service certificates.
###############################################################################
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VAULT_ADDR="${VAULT_ADDR:-http://omni-vault:8200}"
export VAULT_ADDR

ROOT_CA_CN="Omni-Quantum Root CA"
ROOT_CA_ORG="Omni-Quantum Elite"
ROOT_CA_TTL="87600h"           # 10 years
ROOT_CA_MOUNT="pki"

INTERMEDIATE_CA_CN="Omni-Quantum Intermediate CA"
INTERMEDIATE_CA_TTL="17520h"   # 2 years
INTERMEDIATE_CA_MOUNT="pki"

ROLE_NAME="omni-internal"
ROLE_DOMAIN="omni-quantum.internal"
ROLE_MAX_TTL="72h"
ROLE_KEY_TYPE="ec"
ROLE_KEY_BITS="256"

PKI_OFFLINE_DIR="${PKI_OFFLINE_DIR:-/vault/pki-offline}"
CRL_DISTRIBUTION="http://omni-vault:8200/v1/pki/crl"
ISSUING_URL="http://omni-vault:8200/v1/pki/ca"

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
        log_error "setup-pki.sh exited with code $exit_code"
    fi
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
validate_prereqs() {
    log_step "Validating prerequisites"

    if ! command -v vault &>/dev/null; then
        log_error "vault CLI not found in PATH"
        return 1
    fi

    if [[ -z "${VAULT_TOKEN:-}" ]]; then
        log_error "VAULT_TOKEN is not set. Authenticate to Vault first."
        return 1
    fi

    # Verify PKI engine is mounted
    if ! vault secrets list -format=json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'pki/' in d else 1)" 2>/dev/null; then
        log_error "PKI secrets engine not mounted at pki/. Run vault-init.sh first."
        return 1
    fi

    log_ok "Prerequisites validated"
}

# ---------------------------------------------------------------------------
# Step 1: Generate Root CA
# ---------------------------------------------------------------------------
setup_root_ca() {
    log_step "Step 1: Generate Root CA"

    # Tune the PKI engine for the root TTL
    vault secrets tune -max-lease-ttl="${ROOT_CA_TTL}" "${ROOT_CA_MOUNT}"
    log_info "Tuned ${ROOT_CA_MOUNT}/ max-lease-ttl to ${ROOT_CA_TTL}"

    # Check if a root CA already exists
    local existing_ca
    existing_ca=$(vault read -format=json "${ROOT_CA_MOUNT}/cert/ca" 2>/dev/null || echo "{}")
    local has_cert
    has_cert=$(echo "$existing_ca" | python3 -c "
import sys, json
d = json.load(sys.stdin)
cert = d.get('data', {}).get('certificate', '')
print('yes' if cert and 'BEGIN CERTIFICATE' in cert else 'no')
" 2>/dev/null || echo "no")

    if [[ "$has_cert" == "yes" ]]; then
        log_ok "Root CA already exists -- skipping generation"
        return 0
    fi

    # Generate internal root CA
    log_info "Generating Root CA: ${ROOT_CA_CN}"
    local root_output
    root_output=$(vault write -format=json "${ROOT_CA_MOUNT}/root/generate/internal" \
        common_name="${ROOT_CA_CN}" \
        organization="${ROOT_CA_ORG}" \
        ttl="${ROOT_CA_TTL}" \
        key_type="ec" \
        key_bits=384 \
        issuer_name="omni-quantum-root-ca" \
        exclude_cn_from_sans=true)

    # Store root CA certificate offline
    mkdir -p "$PKI_OFFLINE_DIR" 2>/dev/null || true
    local root_cert
    root_cert=$(echo "$root_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['certificate'])" 2>/dev/null)

    if [[ -n "$root_cert" ]]; then
        echo "$root_cert" > "${PKI_OFFLINE_DIR}/omni-quantum-root-ca.pem"
        chmod 400 "${PKI_OFFLINE_DIR}/omni-quantum-root-ca.pem"
        log_ok "Root CA certificate stored offline at ${PKI_OFFLINE_DIR}/omni-quantum-root-ca.pem"
    fi

    # Configure CRL and issuing URLs
    vault write "${ROOT_CA_MOUNT}/config/urls" \
        issuing_certificates="${ISSUING_URL}" \
        crl_distribution_points="${CRL_DISTRIBUTION}"

    log_ok "Root CA generated: ${ROOT_CA_CN} (TTL: ${ROOT_CA_TTL})"
}

# ---------------------------------------------------------------------------
# Step 2: Generate Intermediate CA
# ---------------------------------------------------------------------------
setup_intermediate_ca() {
    log_step "Step 2: Generate Intermediate CA"

    # Generate a CSR for the intermediate CA
    log_info "Generating Intermediate CA CSR: ${INTERMEDIATE_CA_CN}"
    local csr_output
    csr_output=$(vault write -format=json "${INTERMEDIATE_CA_MOUNT}/intermediate/generate/internal" \
        common_name="${INTERMEDIATE_CA_CN}" \
        organization="${ROOT_CA_ORG}" \
        key_type="ec" \
        key_bits=256 \
        issuer_name="omni-quantum-intermediate-ca" \
        exclude_cn_from_sans=true)

    local csr
    csr=$(echo "$csr_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['csr'])" 2>/dev/null)

    if [[ -z "$csr" ]]; then
        log_error "Failed to generate intermediate CSR"
        return 1
    fi

    # Sign the intermediate CSR with the root CA
    log_info "Signing Intermediate CA with Root CA..."
    local signed_output
    signed_output=$(vault write -format=json "${ROOT_CA_MOUNT}/root/sign-intermediate" \
        csr="$csr" \
        format="pem_bundle" \
        ttl="${INTERMEDIATE_CA_TTL}" \
        common_name="${INTERMEDIATE_CA_CN}" \
        organization="${ROOT_CA_ORG}" \
        exclude_cn_from_sans=true)

    local signed_cert
    signed_cert=$(echo "$signed_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['certificate'])" 2>/dev/null)

    if [[ -z "$signed_cert" ]]; then
        log_error "Failed to sign intermediate CA"
        return 1
    fi

    # Import the signed certificate back
    log_info "Importing signed intermediate certificate..."
    vault write "${INTERMEDIATE_CA_MOUNT}/intermediate/set-signed" \
        certificate="$signed_cert"

    # Store intermediate cert offline as well
    if [[ -d "$PKI_OFFLINE_DIR" ]]; then
        echo "$signed_cert" > "${PKI_OFFLINE_DIR}/omni-quantum-intermediate-ca.pem"
        chmod 400 "${PKI_OFFLINE_DIR}/omni-quantum-intermediate-ca.pem"
        log_ok "Intermediate CA certificate stored at ${PKI_OFFLINE_DIR}/omni-quantum-intermediate-ca.pem"
    fi

    log_ok "Intermediate CA generated and signed: ${INTERMEDIATE_CA_CN} (TTL: ${INTERMEDIATE_CA_TTL})"
}

# ---------------------------------------------------------------------------
# Step 3: Create Internal Role
# ---------------------------------------------------------------------------
create_internal_role() {
    log_step "Step 3: Create Internal PKI Role"

    log_info "Creating role: ${ROLE_NAME} for *.${ROLE_DOMAIN}"

    vault write "${INTERMEDIATE_CA_MOUNT}/roles/${ROLE_NAME}" \
        allowed_domains="${ROLE_DOMAIN}" \
        allow_subdomains=true \
        allow_bare_domains=false \
        allow_glob_domains=true \
        allow_wildcard_certificates=true \
        enforce_hostnames=true \
        max_ttl="${ROLE_MAX_TTL}" \
        ttl="24h" \
        key_type="${ROLE_KEY_TYPE}" \
        key_bits="${ROLE_KEY_BITS}" \
        require_cn=true \
        server_flag=true \
        client_flag=true \
        key_usage="DigitalSignature,KeyAgreement,KeyEncipherment" \
        ext_key_usage="ServerAuth,ClientAuth" \
        ou="Omni-Quantum Services" \
        organization="${ROOT_CA_ORG}" \
        generate_lease=true \
        no_store=false

    log_ok "Role created: ${ROLE_NAME} (max TTL: ${ROLE_MAX_TTL}, key: ${ROLE_KEY_TYPE} P-${ROLE_KEY_BITS})"
}

# ---------------------------------------------------------------------------
# Step 4: Issue a test certificate
# ---------------------------------------------------------------------------
test_certificate_issuance() {
    log_step "Step 4: Test Certificate Issuance"

    local test_cn="test-service.${ROLE_DOMAIN}"
    log_info "Issuing test certificate for: ${test_cn}"

    local cert_output
    if cert_output=$(vault write -format=json "${INTERMEDIATE_CA_MOUNT}/issue/${ROLE_NAME}" \
        common_name="$test_cn" \
        ttl="1h" 2>&1); then

        local serial
        serial=$(echo "$cert_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['serial_number'])" 2>/dev/null)
        local expiration
        expiration=$(echo "$cert_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['expiration'])" 2>/dev/null)

        log_ok "Test cert issued: CN=${test_cn}, serial=${serial}, expiry=${expiration}"

        # Revoke the test certificate
        if [[ -n "$serial" ]]; then
            vault write "${INTERMEDIATE_CA_MOUNT}/revoke" serial_number="$serial" &>/dev/null || true
            log_info "Revoked test certificate"
        fi
    else
        log_warn "Test certificate issuance failed (may be expected if DB not fully ready): ${cert_output}"
    fi
}

# ---------------------------------------------------------------------------
# issue-cert function (can be sourced by other scripts)
# ---------------------------------------------------------------------------
issue_cert() {
    # Usage: issue_cert <service-name> [ttl]
    # Example: issue_cert gitea 48h
    local service_name="${1:?Usage: issue_cert <service-name> [ttl]}"
    local ttl="${2:-24h}"
    local cn="${service_name}.${ROLE_DOMAIN:-omni-quantum.internal}"
    local mount="${INTERMEDIATE_CA_MOUNT:-pki}"
    local role="${ROLE_NAME:-omni-internal}"

    local cert_output
    cert_output=$(vault write -format=json "${mount}/issue/${role}" \
        common_name="$cn" \
        alt_names="${service_name}.${ROLE_DOMAIN:-omni-quantum.internal}" \
        ttl="$ttl")

    local certificate
    local private_key
    local ca_chain
    local serial

    certificate=$(echo "$cert_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['certificate'])" 2>/dev/null)
    private_key=$(echo "$cert_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['private_key'])" 2>/dev/null)
    ca_chain=$(echo "$cert_output" | python3 -c "import sys,json; print('\n'.join(json.load(sys.stdin)['data']['ca_chain']))" 2>/dev/null)
    serial=$(echo "$cert_output" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['serial_number'])" 2>/dev/null)

    # Write certificate files to a service-specific directory
    local cert_dir="/vault/certs/${service_name}"
    mkdir -p "$cert_dir" 2>/dev/null || true

    echo "$certificate" > "${cert_dir}/tls.crt"
    echo "$private_key" > "${cert_dir}/tls.key"
    echo "$ca_chain" > "${cert_dir}/ca-chain.pem"

    chmod 644 "${cert_dir}/tls.crt" "${cert_dir}/ca-chain.pem"
    chmod 600 "${cert_dir}/tls.key"

    log_ok "Certificate issued for ${cn} (serial: ${serial}, TTL: ${ttl})"
    log_info "  Certificate : ${cert_dir}/tls.crt"
    log_info "  Private Key : ${cert_dir}/tls.key"
    log_info "  CA Chain    : ${cert_dir}/ca-chain.pem"

    echo "$cert_output"
}

# ---------------------------------------------------------------------------
# Output summary
# ---------------------------------------------------------------------------
output_summary() {
    echo ""
    echo "======================================================================"
    echo " PKI Infrastructure Summary"
    echo "======================================================================"
    echo ""
    echo "  Root CA:"
    echo "    CN           : ${ROOT_CA_CN}"
    echo "    Issuer Name  : omni-quantum-root-ca"
    echo "    TTL          : ${ROOT_CA_TTL} (10 years)"
    echo "    Key Type     : EC P-384"
    echo "    Offline Cert : ${PKI_OFFLINE_DIR}/omni-quantum-root-ca.pem"
    echo ""
    echo "  Intermediate CA:"
    echo "    CN           : ${INTERMEDIATE_CA_CN}"
    echo "    Issuer Name  : omni-quantum-intermediate-ca"
    echo "    TTL          : ${INTERMEDIATE_CA_TTL} (2 years)"
    echo "    Key Type     : EC P-256"
    echo "    Offline Cert : ${PKI_OFFLINE_DIR}/omni-quantum-intermediate-ca.pem"
    echo ""
    echo "  Role: ${ROLE_NAME}"
    echo "    Domain       : *.${ROLE_DOMAIN}"
    echo "    Max TTL      : ${ROLE_MAX_TTL}"
    echo "    Key Type     : ${ROLE_KEY_TYPE} P-${ROLE_KEY_BITS}"
    echo "    Key Usage    : DigitalSignature, KeyAgreement, KeyEncipherment"
    echo "    Ext Key Usage: ServerAuth, ClientAuth"
    echo ""
    echo "  URLs:"
    echo "    CRL          : ${CRL_DISTRIBUTION}"
    echo "    Issuing CA   : ${ISSUING_URL}"
    echo ""
    echo "  Issue a certificate:"
    echo "    source setup-pki.sh && issue_cert <service-name> [ttl]"
    echo "    vault write pki/issue/omni-internal common_name=svc.${ROLE_DOMAIN} ttl=24h"
    echo ""
    echo "======================================================================"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo "======================================================================"
    echo " Omni-Quantum Elite: PKI Infrastructure Setup"
    echo " Vault Address: ${VAULT_ADDR}"
    echo "======================================================================"
    echo ""

    validate_prereqs
    setup_root_ca
    setup_intermediate_ca
    create_internal_role
    test_certificate_issuance
    output_summary

    log_ok "PKI infrastructure setup complete"
}

# Run main only when executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
