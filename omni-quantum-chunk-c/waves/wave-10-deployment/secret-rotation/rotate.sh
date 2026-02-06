#!/bin/bash
# SECRET ROTATION — OMNI QUANTUM ELITE v3.0
set -euo pipefail
VAULT_URL="${VAULT_URL:-http://omni-vault:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
echo "Rotating secrets..."
NEW_SECRET=$(openssl rand -base64 32)
curl -s -X POST "$VAULT_URL/v1/secret/data/omni/api-key" \
    -H "X-Vault-Token: $VAULT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"data\":{\"value\":\"$NEW_SECRET\"}}"
echo "Secret rotation complete"
