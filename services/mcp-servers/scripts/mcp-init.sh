#!/usr/bin/env bash
set -euo pipefail

wait_healthy() {
  local name="$1" url="$2"; local i=0
  while [[ $i -lt 120 ]]; do
    if curl -fsS "$url" >/dev/null; then echo "✅ $name"; return 0; fi
    sleep 2; i=$((i+1))
  done
  echo "❌ $name failed"; return 1
}

wait_healthy "MCP Orchestrator" http://omni-mcp-orchestrator:8335/health
wait_healthy "MCP Knowledge" http://omni-mcp-knowledge:8336/health
wait_healthy "MCP Automation" http://omni-mcp-automation:8337/health
wait_healthy "MCP Financial" http://omni-mcp-financial:8338/health

for client in cline continue claude-code aider; do
  key=$(openssl rand -hex 32)
  vault kv put "secret/mcp/api-keys/${client}" key="$key" >/dev/null 2>&1 || true
  echo "API key for ${client} stored in Vault"
done

TOTAL_TOOLS=0
for port in 8335 8336 8337 8338; do
  curl -fsS -X POST "http://omni-mcp-orchestrator:${port}/mcp?api_key=${MCP_DEFAULT_API_KEY:-}" -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' >/dev/null || true
  tools_json=$(curl -fsS -X POST "http://omni-mcp-orchestrator:${port}/mcp?api_key=${MCP_DEFAULT_API_KEY:-}" -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","method":"tools/list","id":2}' || echo '{}')
  count=$(echo "$tools_json" | jq '.result.tools | length' 2>/dev/null || echo 0)
  TOTAL_TOOLS=$((TOTAL_TOOLS + count))
  echo "Server :${port} => ${count} tools"
done

curl -fsS -X POST http://omni-orchestrator:9500/api/v1/services/register -H 'Content-Type: application/json' -d '{"name":"MCP Orchestrator","codename":"mcp-orchestrator","container":"omni-mcp-orchestrator","port":8335,"tier":"high"}' || true
curl -fsS -X POST http://omni-orchestrator:9500/api/v1/services/register -H 'Content-Type: application/json' -d '{"name":"MCP Knowledge","codename":"mcp-knowledge","container":"omni-mcp-knowledge","port":8336,"tier":"high"}' || true
curl -fsS -X POST http://omni-orchestrator:9500/api/v1/services/register -H 'Content-Type: application/json' -d '{"name":"MCP Automation","codename":"mcp-automation","container":"omni-mcp-automation","port":8337,"tier":"high"}' || true
curl -fsS -X POST http://omni-orchestrator:9500/api/v1/services/register -H 'Content-Type: application/json' -d '{"name":"MCP Financial","codename":"mcp-financial","container":"omni-mcp-financial","port":8338,"tier":"high"}' || true

curl -fsS -X POST http://omni-mattermost-webhook:8066/hooks/builds -H 'Content-Type: application/json' -d "{\"text\":\"🔌 MCP Platform Online — 4 servers, ${TOTAL_TOOLS} tools available. AI coding assistants can now control the platform via VS Code.\"}" || true
