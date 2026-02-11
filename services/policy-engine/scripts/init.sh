#!/usr/bin/env bash
set -euo pipefail
if [ -d /bootstrap-policies ] && [ -d /app/policies ]; then
  cp -n /bootstrap-policies/*.rego /app/policies/ 2>/dev/null || true
fi
echo "[policy-engine] initialization complete"
