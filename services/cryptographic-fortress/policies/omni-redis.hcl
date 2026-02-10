# Policy: omni-redis
# Service: Redis (System 12 - Cache Layer)
# Principle: Read own connection secrets only

path "secret/data/redis/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/redis/*" {
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
