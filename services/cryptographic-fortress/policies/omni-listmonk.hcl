# Policy: omni-listmonk
# Service: Listmonk (Email Newsletter Manager)
# Principle: Read own secrets and database credentials

path "secret/data/listmonk/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/listmonk/*" {
  capabilities = ["read", "list"]
}

path "database/creds/listmonk-readonly" {
  capabilities = ["read"]
}

path "database/creds/listmonk-readwrite" {
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
