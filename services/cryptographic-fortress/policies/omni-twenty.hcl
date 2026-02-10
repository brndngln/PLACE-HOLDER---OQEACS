# Policy: omni-twenty
# Service: Twenty CRM
# Principle: Read own secrets and database credentials

path "secret/data/twenty/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/twenty/*" {
  capabilities = ["read", "list"]
}

path "database/creds/twenty-readonly" {
  capabilities = ["read"]
}

path "database/creds/twenty-readwrite" {
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
