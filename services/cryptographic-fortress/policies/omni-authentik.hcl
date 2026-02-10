# Policy: omni-authentik
# Service: Authentik (System 10 - Identity Provider)
# Principle: Read own secrets and database credentials

path "secret/data/authentik/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/authentik/*" {
  capabilities = ["read", "list"]
}

path "database/creds/authentik-readonly" {
  capabilities = ["read"]
}

path "database/creds/authentik-readwrite" {
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
