# Policy: omni-plane
# Service: Plane (Project Management)
# Principle: Read own secrets and database credentials

path "secret/data/plane/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/plane/*" {
  capabilities = ["read", "list"]
}

path "database/creds/plane-readonly" {
  capabilities = ["read"]
}

path "database/creds/plane-readwrite" {
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
