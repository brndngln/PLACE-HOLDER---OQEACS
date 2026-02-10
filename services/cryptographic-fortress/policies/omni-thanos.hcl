# Policy: omni-thanos
# Service: Thanos (Long-term Metrics Storage)
# Principle: Read own secrets for S3/MinIO and Prometheus configs

path "secret/data/thanos/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/thanos/*" {
  capabilities = ["read", "list"]
}

path "secret/data/minio/access-key" {
  capabilities = ["read"]
}

path "secret/data/minio/secret-key" {
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
