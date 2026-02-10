# Policy: omni-token-infinity
# Service: Token Infinity (Token Management)
# Principle: Read own secrets and API key management

path "secret/data/token-infinity/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/token-infinity/*" {
  capabilities = ["read", "list"]
}

path "secret/data/api-keys/*" {
  capabilities = ["read", "list"]
}

path "transit/encrypt/token-key" {
  capabilities = ["update"]
}

path "transit/decrypt/token-key" {
  capabilities = ["update"]
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
