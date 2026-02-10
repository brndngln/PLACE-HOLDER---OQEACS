# Policy: omni-swe-agent
# Service: SWE-Agent (System 8 - AI Coding Agent)
# Principle: Read own secrets and LiteLLM proxy config for LLM access

path "secret/data/swe-agent/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/swe-agent/*" {
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
