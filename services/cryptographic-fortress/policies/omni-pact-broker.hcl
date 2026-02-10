# Policy: omni-pact-broker
# Service: Pact Broker (Contract Testing)
# Principle: Read own secrets and database credentials

path "secret/data/pact-broker/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/pact-broker/*" {
  capabilities = ["read", "list"]
}

path "database/creds/pact-broker-readonly" {
  capabilities = ["read"]
}

path "database/creds/pact-broker-readwrite" {
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
