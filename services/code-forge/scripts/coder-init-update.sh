#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
wait_healthy() {
  local name="$1" url="$2"; local i=0
  while [[ $i -lt 120 ]]; do
    if curl -fsS "$url" >/dev/null; then echo -e "${GREEN}✅ ${name} healthy${NC}"; return 0; fi
    sleep 2; i=$((i+1))
  done
  echo -e "${YELLOW}⚠️ ${name} not healthy in time${NC}"; return 1
}

wait_healthy "Coder" "http://omni-coder:7080/healthz" || true
coder templates push omni-command --directory /opt/services/code-forge/templates/omni-command
coder templates edit omni-command --default true || true
coder create command-center --template omni-command --parameter cpu=4 --parameter memory=8 --parameter disk=100 || true
coder start command-center || true
coder stat command-center || true
curl -fsS -X POST http://omni-orchestrator:9500/api/v1/services/register -H 'Content-Type: application/json' -d '{"name":"Coder Command Center","codename":"coder-command-center","container":"omni-coder","port":7080,"tier":"high"}' || true
curl -fsS -X POST http://omni-mattermost-webhook:8066/hooks/builds -H 'Content-Type: application/json' -d '{"text":"🖥️ Omni Command Center workspace ready at http://omni-coder:7080/@brendan/command-center"}' || true
