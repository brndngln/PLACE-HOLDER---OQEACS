# Policy: omni-keycloak
# Service: Keycloak (Identity and Access Management)
# Principle: Read own secrets and database credentials

path "secret/data/keycloak/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/keycloak/*" {
  capabilities = ["read", "list"]
}

path "database/creds/keycloak-readonly" {
  capabilities = ["read"]
}

path "database/creds/keycloak-readwrite" {
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
