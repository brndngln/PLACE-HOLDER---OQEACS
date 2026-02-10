# Policy: omni-orchestrator
# Service: Orchestrator (System 15 - Central Orchestration)
# Principle: Broad read access for coordination, manage capabilities for rotation

path "secret/data/*" {
  capabilities = ["read", "list", "create", "update"]
}

path "secret/metadata/*" {
  capabilities = ["read", "list"]
}

path "database/creds/*" {
  capabilities = ["read"]
}

path "pki/issue/omni-internal" {
  capabilities = ["create", "update"]
}

path "transit/encrypt/*" {
  capabilities = ["update"]
}

path "transit/decrypt/*" {
  capabilities = ["update"]
}

path "transit/keys/*" {
  capabilities = ["read"]
}

path "sys/leases/lookup" {
  capabilities = ["update"]
}

path "sys/leases/renew" {
  capabilities = ["update"]
}

# Deny destructive admin operations
path "sys/policy/*" {
  capabilities = ["deny"]
}

path "sys/auth/*" {
  capabilities = ["deny"]
}

path "sys/seal" {
  capabilities = ["deny"]
}
