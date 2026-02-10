# Policy: omni-omi-bridge
# Service: OMI Bridge (System Integration Bridge)
# Principle: Read own secrets and cross-service connection configs

path "secret/data/omi-bridge/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/omi-bridge/*" {
  capabilities = ["read", "list"]
}

path "secret/data/api-keys/*" {
  capabilities = ["read", "list"]
}

path "pki/issue/omni-internal" {
  capabilities = ["create", "update"]
}

path "secret/data/*" {
  capabilities = ["deny"]
}

path "sys/*" {
  capabilities = ["deny"]
}
