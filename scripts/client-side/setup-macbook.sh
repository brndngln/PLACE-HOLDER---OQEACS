#!/usr/bin/env bash
set -euo pipefail

KEY=~/.ssh/omni_quantum_ed25519
SERVER_IP="${1:-}"

if [[ ! -f "$KEY" ]]; then
  ssh-keygen -t ed25519 -f "$KEY" -C "brendan@omni-quantum" -N ""
  echo "Copy this public key to the server:"
  cat "${KEY}.pub"
fi

if [[ -z "$SERVER_IP" ]]; then
  read -rp "Enter server IP: " SERVER_IP
fi

if ! grep -q "Host omni-quantum" ~/.ssh/config 2>/dev/null; then
cat >> ~/.ssh/config <<CONF
Host omni-quantum
  HostName ${SERVER_IP}
  User brendan
  IdentityFile ~/.ssh/omni_quantum_ed25519
  ForwardAgent yes
  ServerAliveInterval 60
  ServerAliveCountMax 10
  LocalForward 9500 localhost:9500
  LocalForward 9501 localhost:9501
  LocalForward 8065 localhost:8065
  LocalForward 3000 localhost:3000
  LocalForward 3001 localhost:3001
  LocalForward 8080 localhost:8080
  LocalForward 7080 localhost:7080
  LocalForward 8335 localhost:8335
  LocalForward 8336 localhost:8336
  LocalForward 8337 localhost:8337
  LocalForward 8338 localhost:8338
  LocalForward 8088 localhost:8088
  LocalForward 4000 localhost:4000
  LocalForward 6333 localhost:6333
CONF
fi

if command -v code >/dev/null 2>&1; then
  code --install-extension ms-vscode-remote.remote-ssh || true
  code --install-extension ms-vscode-remote.remote-ssh-edit || true
fi

cat > ~/omni-quantum.code-workspace <<'JSON'
{
  "folders": [
    {"path": "/home/brendan/platform", "name": "🔧 Platform Source"},
    {"path": "/home/brendan/repos", "name": "📦 All Repositories"},
    {"path": "/home/brendan/projects", "name": "📁 Client Projects"}
  ],
  "settings": {
    "remote.SSH.defaultExtensions": [
      "ms-python.python", "ms-python.vscode-pylance", "charliermarsh.ruff",
      "dbaeumer.vscode-eslint", "esbenp.prettier-vscode", "golang.go", "rust-lang.rust-analyzer",
      "ms-azuretools.vscode-docker", "eamodio.gitlens", "mhutchie.git-graph",
      "humao.rest-client", "rangav.vscode-thunder-client", "usernamehw.errorlens",
      "gruntfuggly.todo-tree", "redhat.vscode-yaml", "tamasfe.even-better-toml"
    ],
    "remote.SSH.remotePlatform": {"omni-quantum": "linux"},
    "terminal.integrated.defaultProfile.linux": "bash",
    "editor.formatOnSave": true,
    "git.autofetch": true
  }
}
JSON

ssh omni-quantum "echo '✅ Connected to Omni Quantum Elite'" || echo "❌ Connection failed"

echo "✅ MacBook configured for Omni Quantum Elite"
echo "To connect:"
echo "  1. Open VS Code"
echo "  2. Ctrl+Shift+P → Remote-SSH: Connect to Host → omni-quantum"
echo "  3. Open workspace: ~/omni-quantum.code-workspace"
