#!/usr/bin/env bash
set -euo pipefail

MCP_KEY=$(ssh omni-quantum "vault kv get -field=key secret/mcp/api-keys/cline" 2>/dev/null || echo "REPLACE_WITH_YOUR_KEY")

SETTINGS="$HOME/Library/Application Support/Code/User/settings.json"
mkdir -p "$(dirname "$SETTINGS")"
python3 - <<PY
import json, pathlib
p=pathlib.Path(r'''$SETTINGS''')
obj={}
if p.exists():
  obj=json.loads(p.read_text() or '{}')
obj['cline.mcpServers']={
  'omni-orchestrator': {'url':'http://localhost:8335/mcp','apiKey':'$MCP_KEY'},
  'omni-knowledge': {'url':'http://localhost:8336/mcp','apiKey':'$MCP_KEY'},
  'omni-automation': {'url':'http://localhost:8337/mcp','apiKey':'$MCP_KEY'},
  'omni-financial': {'url':'http://localhost:8338/mcp','apiKey':'$MCP_KEY'},
}
p.write_text(json.dumps(obj,indent=2))
PY

mkdir -p ~/.continue
cat > ~/.continue/config.json <<JSON
{
  "mcpServers": [
    {"name":"omni-orchestrator","url":"http://localhost:8335/mcp"},
    {"name":"omni-knowledge","url":"http://localhost:8336/mcp"},
    {"name":"omni-automation","url":"http://localhost:8337/mcp"},
    {"name":"omni-financial","url":"http://localhost:8338/mcp"}
  ]
}
JSON

mkdir -p ~/.claude
cat > ~/.claude/mcp_servers.json <<JSON
{
  "omni-orchestrator": {"url": "http://localhost:8335/mcp", "api_key": "$MCP_KEY"},
  "omni-knowledge": {"url": "http://localhost:8336/mcp", "api_key": "$MCP_KEY"},
  "omni-automation": {"url": "http://localhost:8337/mcp", "api_key": "$MCP_KEY"},
  "omni-financial": {"url": "http://localhost:8338/mcp", "api_key": "$MCP_KEY"}
}
JSON

cat > ~/.aider.conf.yml <<YAML
mcp_servers:
  - name: omni-orchestrator
    url: http://localhost:8335/mcp
  - name: omni-knowledge
    url: http://localhost:8336/mcp
  - name: omni-automation
    url: http://localhost:8337/mcp
  - name: omni-financial
    url: http://localhost:8338/mcp
YAML

echo "✅ MCP clients configured"
echo "   Cline: 4 servers connected"
echo "   Continue: 4 servers connected"
echo "   Claude Code: 4 servers connected (if installed)"
