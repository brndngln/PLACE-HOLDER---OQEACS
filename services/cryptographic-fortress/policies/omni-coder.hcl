# Policy: omni-coder
# Service: Coder (Cloud Development Environments)
# Principle: Read own secrets and database credentials

path "secret/data/coder/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/coder/*" {
  capabilities = ["read", "list"]
}

path "secret/data/gitea/token" {
  capabilities = ["read"]
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
