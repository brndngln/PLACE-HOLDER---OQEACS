# Policy: omni-openhands
# Service: OpenHands (System 8 - AI Coding Agent)
# Principle: Read own secrets and LiteLLM proxy config for LLM access

path "secret/data/openhands/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/openhands/*" {
  capabilities = ["read", "list"]
}

path "secret/data/litellm/*" {
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
