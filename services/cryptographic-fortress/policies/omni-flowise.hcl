# Policy: omni-flowise
# Service: Flowise (AI Workflow Builder)
# Principle: Read own secrets and API keys for LLM access

path "secret/data/flowise/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/flowise/*" {
  capabilities = ["read", "list"]
}

path "secret/data/api-keys/*" {
  capabilities = ["read", "list"]
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
