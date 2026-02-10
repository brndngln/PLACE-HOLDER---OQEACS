# Policy: omni-grafana
# Service: Grafana (System 6 - Observatory)
# Principle: Read own secrets for datasource configs

path "secret/data/grafana/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/grafana/*" {
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
