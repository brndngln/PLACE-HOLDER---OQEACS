terraform {
  required_providers {
    coder = {
      source = "coder/coder"
    }
  }
}

data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

resource "coder_parameter" "cpu" {
  name         = "cpu"
  display_name = "CPU Cores"
  type         = "number"
  default      = "4"
  mutable      = true
}

resource "coder_parameter" "memory" {
  name         = "memory"
  display_name = "Memory (GB)"
  type         = "number"
  default      = "8"
  mutable      = true
}

resource "coder_parameter" "disk" {
  name         = "disk"
  display_name = "Disk (GB)"
  type         = "number"
  default      = "100"
  mutable      = true
}

resource "coder_agent" "dev" {
  os   = "linux"
  arch = "amd64"

  startup_script = <<-EOT
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive
    sudo apt-get update
    sudo apt-get install -y curl wget jq yq git tmux htop ripgrep fd-find fzf bat redis-tools postgresql-client httpie unzip zip build-essential ca-certificates gnupg lsb-release

    # Python toolchain
    sudo apt-get install -y python3.12 python3-pip python3-venv
    python3 -m pip install --user --upgrade pip poetry ruff black mypy pytest ipython

    # Node.js 20
    if ! command -v node >/dev/null 2>&1; then
      curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
      sudo apt-get install -y nodejs
    fi
    npm i -g pnpm tsx eslint prettier

    # Go
    if ! command -v go >/dev/null 2>&1; then
      curl -fsSL https://go.dev/dl/go1.22.6.linux-amd64.tar.gz | sudo tar -C /usr/local -xz
      echo 'export PATH=/usr/local/go/bin:$PATH' >> ~/.bashrc
    fi
    /usr/local/go/bin/go install golang.org/x/tools/gopls@latest || true
    /usr/local/go/bin/go install github.com/go-delve/delve/cmd/dlv@latest || true
    /usr/local/go/bin/go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest || true

    # Rust
    if ! command -v rustup >/dev/null 2>&1; then
      curl https://sh.rustup.rs -sSf | sh -s -- -y
      source "$HOME/.cargo/env"
    fi
    rustup component add clippy rustfmt rust-analyzer || true

    # Java
    sudo apt-get install -y openjdk-21-jdk

    # Docker CLI + compose plugin
    sudo apt-get install -y docker.io docker-compose-plugin || true

    # Optional CLIs
    command -v mc >/dev/null || (curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o mc && chmod +x mc && sudo mv mc /usr/local/bin/mc)
    command -v mmctl >/dev/null || (curl -fsSL https://releases.mattermost.com/mmctl/9.8.0/mmctl-9.8.0-linux-amd64.tar.gz | tar -xz && sudo mv mmctl /usr/local/bin/mmctl)
    command -v k6 >/dev/null || sudo apt-get install -y k6 || true
    command -v trivy >/dev/null || true

    mkdir -p /home/coder/repos /home/coder/.omni /home/coder/.vscode
    cp -f /opt/template/home-config/.omni/env.sh /home/coder/.omni/env.sh
    cp -f /opt/template/home-config/.omni/aliases.sh /home/coder/.omni/aliases.sh

    cat >/home/coder/.vscode/settings.json <<'JSON'
    {
      "terminal.integrated.defaultProfile.linux": "bash",
      "editor.formatOnSave": true,
      "git.autofetch": true,
      "git.fetchOnPull": true,
      "editor.minimap.enabled": false,
      "editor.rulers": [80, 120],
      "files.exclude": {
        "**/__pycache__": true,
        "**/node_modules": true,
        "**/.venv": true,
        "**/.git": true
      }
    }
    JSON

    /opt/template/startup.sh || true
  EOT
}

resource "coder_app" "code" {
  agent_id     = coder_agent.dev.id
  slug         = "vscode"
  display_name = "VS Code"
  icon         = "/icon/code.svg"
  url          = "http://localhost:13337/?folder=/home/coder/repos"
  share        = "owner"
}

resource "coder_metadata" "labels" {
  resource_id = coder_agent.dev.id
  item {
    key   = "omni.quantum.component"
    value = "coder-workspace"
  }
  item {
    key   = "omni.quantum.tier"
    value = "high"
  }
  item {
    key   = "omni.quantum.critical"
    value = "false"
  }
}
