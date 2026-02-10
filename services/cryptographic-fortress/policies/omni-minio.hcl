# Policy: omni-minio
# Service: MinIO (System 13 - Object Store)
# Principle: Read own access/secret keys only

path "secret/data/minio/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/minio/*" {
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
