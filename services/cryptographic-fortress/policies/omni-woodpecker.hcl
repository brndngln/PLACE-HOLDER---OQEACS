# Policy: omni-woodpecker
# Service: Woodpecker CI (System 7 - Code Fortress CI/CD)
# Principle: Read own secrets and gitea token for repo access

path "secret/data/woodpecker/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/woodpecker/*" {
  capabilities = ["read", "list"]
}

path "secret/data/gitea/token" {
  capabilities = ["read"]
}

path "database/creds/woodpecker-readonly" {
  capabilities = ["read"]
}

path "database/creds/woodpecker-readwrite" {
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
