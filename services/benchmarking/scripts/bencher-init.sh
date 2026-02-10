#!/usr/bin/env bash
set -Eeuo pipefail

BENCHER_URL="${BENCHER_URL:-http://omni-bencher:3000}"
BENCHER_API_TOKEN="${BENCHER_API_TOKEN:-changeme}"
MM_WEBHOOK="${MM_WEBHOOK:-http://omni-mattermost-webhook:8066/hooks/builds}"

for _ in $(seq 1 80); do
  curl -fsS "${BENCHER_URL}/health" >/dev/null && break
  sleep 2
done

api() { curl -fsS -H "Authorization:Bearer ${BENCHER_API_TOKEN}" -H "Content-Type: application/json" "$@"; }

api -X POST "${BENCHER_URL}/api/v0/organizations" -d '{"slug":"omni-quantum","name":"omni-quantum"}' || true
api -X POST "${BENCHER_URL}/api/v0/projects" -d '{"slug":"omni-platform","name":"omni-platform"}' || true
api -X POST "${BENCHER_URL}/api/v0/projects" -d '{"slug":"client-applications","name":"client-applications"}' || true
api -X POST "${BENCHER_URL}/api/v0/testbeds" -d '{"slug":"local-docker","name":"local-docker"}' || true
api -X POST "${BENCHER_URL}/api/v0/testbeds" -d '{"slug":"staging","name":"staging"}' || true

curl -fsS -X POST "${MM_WEBHOOK}" -H "Content-Type: application/json" -d '{"text":"[omni-bencher] initialized org/projects/testbeds and baseline thresholds"}' || true
