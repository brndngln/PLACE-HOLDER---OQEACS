# Policy: omni-chatwoot
# Service: Chatwoot (Customer Support Chat)
# Principle: Read own secrets and database credentials

path "secret/data/chatwoot/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/chatwoot/*" {
  capabilities = ["read", "list"]
}

path "database/creds/chatwoot-readonly" {
  capabilities = ["read"]
}

path "database/creds/chatwoot-readwrite" {
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
