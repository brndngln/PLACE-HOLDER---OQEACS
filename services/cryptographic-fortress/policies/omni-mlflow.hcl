# Policy: omni-mlflow
# Service: MLflow (ML Experiment Tracking)
# Principle: Read own secrets and database credentials

path "secret/data/mlflow/*" {
  capabilities = ["read", "list"]
}

path "secret/metadata/mlflow/*" {
  capabilities = ["read", "list"]
}

path "database/creds/mlflow-readonly" {
  capabilities = ["read"]
}

path "database/creds/mlflow-readwrite" {
  capabilities = ["read"]
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
