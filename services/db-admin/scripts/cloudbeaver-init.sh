#!/usr/bin/env bash
set -Eeuo pipefail

CLOUDBEAVER_URL="${CLOUDBEAVER_URL:-http://omni-cloudbeaver:8978}"
MM_WEBHOOK="${MM_WEBHOOK:-http://omni-mattermost-webhook:8066/hooks/builds}"

for _ in $(seq 1 120); do
  if curl -fsS "$CLOUDBEAVER_URL/status" >/dev/null; then
    break
  fi
  sleep 2
done

mkdir -p /tmp/cloudbeaver
cat > /tmp/cloudbeaver/connections.json <<'JSON'
{
  "connections": [
    {"name": "omni-postgres-main", "host": "omni-postgres", "port": 5432, "database": "omni", "readonly_secret": "database/creds/main-readonly"},
    {"name": "omni-postgres-financial", "host": "omni-postgres-financial", "port": 5432, "database": "financial", "readonly_secret": "database/creds/financial-readonly"},
    {"name": "omni-postgres-audit", "host": "omni-postgres-audit", "port": 5432, "database": "audit", "readonly_secret": "database/creds/audit-readonly"},
    {"name": "omni-postgres-mlflow", "host": "omni-mlflow-postgres", "port": 5432, "database": "mlflow", "readonly_secret": "database/creds/mlflow-readonly"},
    {"name": "omni-postgres-kong", "host": "omni-kong-postgres", "port": 5432, "database": "kong", "readonly_secret": "database/creds/kong-readonly"},
    {"name": "omni-postgres-pact", "host": "omni-pact-postgres", "port": 5432, "database": "pact", "readonly_secret": "database/creds/pact-readonly"}
  ],
  "roles": ["admin", "developer", "viewer"],
  "sso": "authentik-forward-auth"
}
JSON

echo "[cloudbeaver-init] prepared readonly connection + role templates"
echo "[cloudbeaver-init] configure Traefik route /db-admin + Authentik forward-auth in gateway-sentinel"
curl -fsS -X POST "$MM_WEBHOOK" -H 'Content-Type: application/json' -d '{"text":"[cloudbeaver-init] DB admin readonly profiles configured"}' || true
