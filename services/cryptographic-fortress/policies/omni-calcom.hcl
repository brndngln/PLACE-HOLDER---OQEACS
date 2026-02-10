# Policy: omni-calcom
# Service: Cal.com (Scheduling)
# Principle: Read own secrets and database credentials

path "secret/data/calcom/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/calcom/*" {
  capabilities = ["read", "list"]
}

path "database/creds/calcom-readonly" {
  capabilities = ["read"]
}

path "database/creds/calcom-readwrite" {
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
