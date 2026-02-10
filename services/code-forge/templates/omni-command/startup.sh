#!/usr/bin/env bash
set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; NC='\033[0m'

source /home/coder/.omni/env.sh || true
source /home/coder/.omni/aliases.sh || true

mkdir -p /home/coder/repos

if [[ -n "${GITEA_EMAIL:-}" ]]; then
  git config --global user.email "$GITEA_EMAIL"
else
  git config --global user.email "brendan@omni.local"
fi
git config --global user.name "Brendan"
git config --global credential.helper store
if [[ -n "${GITEA_TOKEN:-}" ]]; then
  printf "http://%s:%s@omni-gitea:3000\n" "brendan" "$GITEA_TOKEN" > /home/coder/.git-credentials
fi

if [[ -n "${MINIO_ACCESS_KEY:-}" && -n "${MINIO_SECRET_KEY:-}" ]]; then
  mc alias set omni http://omni-minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null 2>&1 || true
fi

BASE_REPOS=(
  "omni-platform"
  "omni-configs"
  "omni-knowledge"
  "client-template"
)

for repo in "${BASE_REPOS[@]}"; do
  if [[ ! -d "/home/coder/repos/${repo}/.git" ]]; then
    git clone "http://omni-gitea:3000/omni-quantum/${repo}.git" "/home/coder/repos/${repo}" >/dev/null 2>&1 || true
  fi
  git -C "/home/coder/repos/${repo}" pull --ff-only >/dev/null 2>&1 || true
done

repo_json="$(curl -fsS "http://omni-gitea:3000/api/v1/repos/search?limit=50" || echo '{}')"
for repo in $(echo "$repo_json" | jq -r '.data[]?.name'); do
  if [[ ! -d "/home/coder/repos/${repo}/.git" ]]; then
    git clone "http://omni-gitea:3000/omni-quantum/${repo}.git" "/home/coder/repos/${repo}" >/dev/null 2>&1 || true
  fi
  git -C "/home/coder/repos/${repo}" pull --ff-only >/dev/null 2>&1 || true
done

healthy_count="$(curl -fsS http://omni-orchestrator:9500/api/v1/status 2>/dev/null | jq '[.[] | select(.health_status=="healthy")] | length' 2>/dev/null || echo 0)"
total_count="$(curl -fsS http://omni-orchestrator:9500/api/v1/status 2>/dev/null | jq 'length' 2>/dev/null || echo 0)"
vram_used="$(curl -fsS http://omni-model-manager:11435/gpu/status 2>/dev/null | jq '.vram_used_bytes/1073741824|floor' 2>/dev/null || echo 0)"
vram_total="$(curl -fsS http://omni-model-manager:11435/gpu/status 2>/dev/null | jq '.vram_total_bytes/1073741824|floor' 2>/dev/null || echo 0)"
loaded_models="$(curl -fsS http://omni-model-manager:11435/models 2>/dev/null | jq '[.[] | select(.loaded==true)] | length' 2>/dev/null || echo 0)"

echo -e "${BLUE}⚛️  Omni Quantum Elite — Command Center v1.0${NC}"
echo -e "   Platform: ${healthy_count}/${total_count} services healthy"
echo -e "   GPU: ${vram_used}GB / ${vram_total}GB VRAM"
echo -e "   Models: ${loaded_models} loaded"
echo -e "   Type 'omni-help' for commands${NC}"
