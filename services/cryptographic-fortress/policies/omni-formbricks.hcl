# Policy: omni-formbricks
# Service: Formbricks (Survey & Forms Platform)
# Principle: Read own secrets and database credentials

path "secret/data/formbricks/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/formbricks/*" {
  capabilities = ["read", "list"]
}

path "database/creds/formbricks-readonly" {
  capabilities = ["read"]
}

path "database/creds/formbricks-readwrite" {
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
