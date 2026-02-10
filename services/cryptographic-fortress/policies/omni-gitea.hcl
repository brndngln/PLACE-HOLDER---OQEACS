# Policy: omni-gitea
# Service: Gitea (System 7 - Code Fortress)
# Principle: Least privilege - read own secrets, DB creds, PKI for TLS

path "secret/data/gitea/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/gitea/*" {
  capabilities = ["read", "list"]
}

path "database/creds/gitea-readonly" {
  capabilities = ["read"]
}

path "database/creds/gitea-readwrite" {
  capabilities = ["read"]
}

path "pki/issue/omni-internal" {
  capabilities = ["create", "update"]
}

# Deny everything else explicitly
path "secret/data/*" {
  capabilities = ["deny"]
}

path "sys/*" {
  capabilities = ["deny"]
}
