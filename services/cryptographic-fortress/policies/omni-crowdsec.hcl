# Policy: omni-crowdsec
# Service: CrowdSec (System 9 - Security Shield)
# Principle: Read own secrets for API keys and bouncer configs

path "secret/data/crowdsec/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/crowdsec/*" {
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
