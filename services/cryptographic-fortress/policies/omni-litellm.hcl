# Policy: omni-litellm
# Service: LiteLLM (System 3 - AI Gateway)
# Principle: Read own secrets and API keys for LLM provider routing

path "secret/data/litellm/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/litellm/*" {
  capabilities = ["read", "list"]
}

path "secret/data/api-keys/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/api-keys/*" {
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
