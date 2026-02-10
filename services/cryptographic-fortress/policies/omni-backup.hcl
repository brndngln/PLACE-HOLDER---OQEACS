# Policy: omni-backup
# Service: Backup Fortress (System 5)
# Principle: Broader read access needed for backup operations across all services

path "secret/data/*" {
  capabilities = ["read", "list"]
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

path "transit/encrypt/backup-key" {
  capabilities = ["update"]
}

path "transit/decrypt/backup-key" {
  capabilities = ["update"]
}

# Deny admin operations
path "sys/policy/*" {
  capabilities = ["deny"]
}

path "auth/*" {
  capabilities = ["deny"]
}
