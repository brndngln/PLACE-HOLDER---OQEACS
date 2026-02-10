# Policy: omni-wikijs
# Service: Wiki.js (Knowledge Base)
# Principle: Read own secrets and database credentials

path "secret/data/wikijs/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/wikijs/*" {
  capabilities = ["read", "list"]
}

path "database/creds/wikijs-readonly" {
  capabilities = ["read"]
}

path "database/creds/wikijs-readwrite" {
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
