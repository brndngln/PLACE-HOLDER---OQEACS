# Policy: omni-qdrant
# Service: Qdrant (Vector Database)
# Principle: Read own API keys and connection secrets

path "secret/data/qdrant/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/qdrant/*" {
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
