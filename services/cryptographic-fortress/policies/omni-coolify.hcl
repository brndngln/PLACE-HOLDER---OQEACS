# Policy: omni-coolify
# Service: Coolify (Self-hosted PaaS)
# Principle: Read own secrets for deployment and server configs

path "secret/data/coolify/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/coolify/*" {
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
