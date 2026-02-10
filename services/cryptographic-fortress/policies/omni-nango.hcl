# Policy: omni-nango
# Service: Nango (Integration Platform)
# Principle: Read own secrets for third-party API integrations

path "secret/data/nango/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/nango/*" {
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
