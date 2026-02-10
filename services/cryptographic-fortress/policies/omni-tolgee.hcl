# Policy: omni-tolgee
# Service: Tolgee (Localization Platform)
# Principle: Read own secrets and database credentials

path "secret/data/tolgee/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/tolgee/*" {
  capabilities = ["read", "list"]
}

path "database/creds/tolgee-readonly" {
  capabilities = ["read"]
}

path "database/creds/tolgee-readwrite" {
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
