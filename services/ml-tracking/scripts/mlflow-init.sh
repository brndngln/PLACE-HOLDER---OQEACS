#!/usr/bin/env bash
set -Eeuo pipefail

MLFLOW_URL="${MLFLOW_URL:-http://omni-mlflow:5000}"
MM_WEBHOOK="${MM_WEBHOOK:-http://omni-mattermost-webhook:8066/hooks/quality}"

for _ in $(seq 1 80); do
  curl -fsS "${MLFLOW_URL}/health" >/dev/null && break
  sleep 2
done

curl -fsS -X POST "http://omni-experiment-tracker:5001/init" -H "Content-Type: application/json" -d '{}'
curl -fsS -X POST "${MM_WEBHOOK}" -H "Content-Type: application/json" -d '{"text":"[omni-mlflow] experiments initialized"}' || true
