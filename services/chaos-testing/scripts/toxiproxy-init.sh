#!/usr/bin/env bash
set -Eeuo pipefail

TOXI_URL="${TOXI_URL:-http://omni-toxiproxy:8474}"
MM_WEBHOOK="${MM_WEBHOOK:-http://omni-mattermost-webhook:8066/hooks/builds}"

for _ in $(seq 1 50); do
  curl -fsS "${TOXI_URL}/proxies" >/dev/null && break
  sleep 2
done

create_proxy() {
  local name="$1" listen="$2" upstream="$3"
  curl -fsS -X POST "${TOXI_URL}/proxies" -H "Content-Type: application/json" \
    -d "{\"name\":\"${name}\",\"listen\":\"0.0.0.0:${listen}\",\"upstream\":\"${upstream}\"}" || true
}

create_proxy postgres-proxy 15432 omni-postgres:5432
create_proxy redis-proxy 16379 omni-redis:6379
create_proxy qdrant-proxy 16333 omni-qdrant:6333
create_proxy ollama-proxy 21434 omni-ollama:11434
create_proxy litellm-proxy 14000 omni-litellm:4000
create_proxy minio-proxy 19000 omni-minio:9000
create_proxy gitea-proxy 13000 omni-gitea:3000
create_proxy vault-proxy 18200 omni-vault:8200

curl -fsS -X POST "${MM_WEBHOOK}" -H "Content-Type: application/json" -d '{"text":"[omni-toxiproxy] proxy initialization completed"}' || true
