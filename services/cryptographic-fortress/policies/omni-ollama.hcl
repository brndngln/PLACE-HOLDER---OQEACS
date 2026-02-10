# Policy: omni-ollama
# Service: Ollama (Local LLM Runtime)
# Principle: Read own config secrets only

path "secret/data/ollama/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/ollama/*" {
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
