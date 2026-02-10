# Policy: omni-langfuse
# Service: Langfuse (System 4 - AI Observability)
# Principle: Read own secrets and database credentials

path "secret/data/langfuse/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/langfuse/*" {
  capabilities = ["read", "list"]
}

path "database/creds/langfuse-readonly" {
  capabilities = ["read"]
}

path "database/creds/langfuse-readwrite" {
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
