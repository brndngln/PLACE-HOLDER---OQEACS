# Policy: omni-superset
# Service: Apache Superset (Data Visualization)
# Principle: Read own secrets and database credentials

path "secret/data/superset/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/superset/*" {
  capabilities = ["read", "list"]
}

path "database/creds/superset-readonly" {
  capabilities = ["read"]
}

path "database/creds/superset-readwrite" {
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
