# Policy: omni-portainer
# Service: Portainer (Container Management)
# Principle: Read own secrets for Docker/Swarm management

path "secret/data/portainer/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/portainer/*" {
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
