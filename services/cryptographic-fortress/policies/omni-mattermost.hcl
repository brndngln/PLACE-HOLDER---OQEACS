# Policy: omni-mattermost
# Service: Mattermost (System 11 - Team Communication)
# Principle: Read own secrets and database credentials

path "secret/data/mattermost/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/mattermost/*" {
  capabilities = ["read", "list"]
}

path "database/creds/mattermost-readonly" {
  capabilities = ["read"]
}

path "database/creds/mattermost-readwrite" {
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
