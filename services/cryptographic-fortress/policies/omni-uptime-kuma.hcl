# Policy: omni-uptime-kuma
# Service: Uptime Kuma (Uptime Monitoring)
# Principle: Read own secrets for notification and monitoring configs

path "secret/data/uptime-kuma/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/uptime-kuma/*" {
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
