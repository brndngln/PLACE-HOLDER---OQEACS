# Policy: omni-crater
# Service: Crater (Invoicing)
# Principle: Read own secrets and database credentials

path "secret/data/crater/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/crater/*" {
  capabilities = ["read", "list"]
}

path "database/creds/crater-readonly" {
  capabilities = ["read"]
}

path "database/creds/crater-readwrite" {
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
