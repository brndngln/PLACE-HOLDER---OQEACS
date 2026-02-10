# Policy: omni-glitchtip
# Service: GlitchTip (Error Tracking)
# Principle: Read own secrets and database credentials

path "secret/data/glitchtip/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/glitchtip/*" {
  capabilities = ["read", "list"]
}

path "database/creds/glitchtip-readonly" {
  capabilities = ["read"]
}

path "database/creds/glitchtip-readwrite" {
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
