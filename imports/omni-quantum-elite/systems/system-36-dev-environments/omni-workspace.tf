###############################################################################
# Coder Workspace Template — Omni Quantum Dev Environment
# Pre-configured Docker workspace with all tools for AI-generated projects
###############################################################################

terraform {
  required_providers {
    coder = {
      source = "coder/coder"
    }
    docker = {
      source = "kreuzwerker/docker"
    }
  }
}

data "coder_provisioner" "me" {}

provider "docker" {}

data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
data "coder_parameter" "language" {
  name         = "language"
  display_name = "Primary Language"
  description  = "Choose the primary language for your workspace"
  default      = "python"
  mutable      = false
  option {
    name  = "Python"
    value = "python"
    icon  = "/icon/python.svg"
  }
  option {
    name  = "Node.js"
    value = "nodejs"
    icon  = "/icon/nodejs.svg"
  }
  option {
    name  = "Go"
    value = "golang"
    icon  = "/icon/go.svg"
  }
  option {
    name  = "Rust"
    value = "rust"
    icon  = "/icon/rust.svg"
  }
  option {
    name  = "Full Stack"
    value = "fullstack"
    icon  = "/icon/code.svg"
  }
}

data "coder_parameter" "cpu" {
  name         = "cpu"
  display_name = "CPU Cores"
  default      = "4"
  mutable      = true
  option {
    name  = "2 cores"
    value = "2"
  }
  option {
    name  = "4 cores"
    value = "4"
  }
  option {
    name  = "8 cores"
    value = "8"
  }
}

data "coder_parameter" "memory" {
  name         = "memory"
  display_name = "Memory (GB)"
  default      = "8"
  mutable      = true
  option {
    name  = "4 GB"
    value = "4"
  }
  option {
    name  = "8 GB"
    value = "8"
  }
  option {
    name  = "16 GB"
    value = "16"
  }
}

data "coder_parameter" "gpu" {
  name         = "gpu"
  display_name = "GPU Access"
  description  = "Enable GPU passthrough for AI model testing"
  default      = "false"
  mutable      = true
  option {
    name  = "No GPU"
    value = "false"
  }
  option {
    name  = "GPU Enabled"
    value = "true"
  }
}

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
resource "coder_agent" "main" {
  arch           = data.coder_provisioner.me.arch
  os             = "linux"
  startup_script = <<-EOT
    #!/bin/bash
    set -e

    # Install code-server (VS Code in browser)
    if ! command -v code-server &>/dev/null; then
      curl -fsSL https://code-server.dev/install.sh | sh
    fi
    code-server --auth none --port 13337 --host 0.0.0.0 &

    # Configure Git
    git config --global user.name "${data.coder_workspace_owner.me.full_name}"
    git config --global user.email "${data.coder_workspace_owner.me.email}"
    git config --global init.defaultBranch main

    # Language-specific setup
    case "${data.coder_parameter.language.value}" in
      python)
        pip install --upgrade pip
        pip install ruff mypy pytest pytest-cov httpx fastapi uvicorn
        ;;
      nodejs)
        npm install -g pnpm typescript eslint prettier
        ;;
      golang)
        go install golang.org/x/tools/gopls@latest
        go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
        ;;
      rust)
        rustup component add rustfmt clippy rust-analyzer
        ;;
      fullstack)
        pip install --upgrade pip ruff mypy pytest httpx fastapi
        npm install -g pnpm typescript eslint prettier
        ;;
    esac

    # Install common dev tools
    apt-get update -qq && apt-get install -y -qq jq ripgrep fd-find httpie 2>/dev/null || true

    # Configure Omni Quantum CLI
    if command -v omni &>/dev/null; then
      omni configure --auto
    fi

    echo "✅ Workspace ready!"
  EOT

  metadata {
    display_name = "CPU Usage"
    key          = "cpu"
    script       = "coder stat cpu"
    interval     = 10
    timeout      = 1
  }
  metadata {
    display_name = "Memory Usage"
    key          = "mem"
    script       = "coder stat mem"
    interval     = 10
    timeout      = 1
  }
  metadata {
    display_name = "Disk Usage"
    key          = "disk"
    script       = "coder stat disk --path /home/coder"
    interval     = 60
    timeout      = 1
  }
}

resource "coder_app" "code-server" {
  agent_id     = coder_agent.main.id
  slug         = "code-server"
  display_name = "VS Code"
  url          = "http://localhost:13337/?folder=/home/coder/project"
  icon         = "/icon/code.svg"
  subdomain    = false
  share        = "owner"
}

# ---------------------------------------------------------------------------
# Docker Container
# ---------------------------------------------------------------------------
resource "docker_image" "workspace" {
  name = "omni-workspace-${data.coder_parameter.language.value}:latest"
  build {
    context = "."
    build_args = {
      LANGUAGE = data.coder_parameter.language.value
    }
  }
}

resource "docker_container" "workspace" {
  count = data.coder_workspace.me.start_count
  image = docker_image.workspace.image_id
  name  = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"

  entrypoint = ["sh", "-c", replace(coder_agent.main.init_script, "/localhost|127\\.0\\.0\\.1/", "host.docker.internal")]
  env        = ["CODER_AGENT_TOKEN=${coder_agent.main.token}"]

  host {
    host = "host.docker.internal"
    ip   = "host-gateway"
  }

  # Resource limits
  cpu_shares = data.coder_parameter.cpu.value * 1024
  memory     = data.coder_parameter.memory.value * 1024

  # Network access to Omni Quantum services
  networks_advanced {
    name = "omni-quantum-network"
  }

  # Persistent home directory
  volumes {
    container_path = "/home/coder"
    volume_name    = docker_volume.home.name
    read_only      = false
  }
}

resource "docker_volume" "home" {
  name = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}-home"
}
