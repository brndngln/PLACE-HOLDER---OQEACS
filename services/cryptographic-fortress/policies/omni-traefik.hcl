# Policy: omni-traefik
# Service: Traefik (System 1 - Gateway Sentinel)
# Principle: Read own secrets and issue TLS certificates

path "secret/data/traefik/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/traefik/*" {
  capabilities = ["read", "list"]
}

path "pki/issue/omni-internal" {
  capabilities = ["create", "update"]
}

path "pki/cert/*" {
  capabilities = ["read"]
}

path "secret/data/*" {
  capabilities = ["deny"]
}

path "sys/*" {
  capabilities = ["deny"]
}
