# Policy: omni-n8n
# Service: n8n (System 14 - Workflow Automation)
# Principle: Read own secrets and database credentials

path "secret/data/n8n/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/n8n/*" {
  capabilities = ["read", "list"]
}

path "database/creds/n8n-readonly" {
  capabilities = ["read"]
}

path "database/creds/n8n-readwrite" {
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
