# Policy: omni-prometheus
# Service: Prometheus (System 6 - Observatory)
# Principle: Read own secrets for scrape configs and remote write

path "secret/data/prometheus/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/prometheus/*" {
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
