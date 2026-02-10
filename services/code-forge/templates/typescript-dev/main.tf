terraform {
  required_providers {
    coder = {
      source  = "coder/coder"
      version = ">= 0.12.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 3.0.0"
    }
  }
}

# ---------------------------------------------------------------------------
# Coder provider data sources
# ---------------------------------------------------------------------------

data "coder_provisioner" "me" {}

data "coder_workspace" "me" {}

data "coder_workspace_owner" "me" {}

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

variable "node_version" {
  description = "Node.js version to install"
  type        = string
  default     = "20"
  validation {
    condition     = contains(["18", "20", "22"], var.node_version)
    error_message = "Supported Node.js versions: 18, 20, 22"
  }
}

variable "git_repo" {
  description = "Git repository URL to clone (optional)"
  type        = string
  default     = ""
}

variable "dotfiles_repo" {
  description = "Dotfiles repository URL (optional)"
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------
# Docker provider
# ---------------------------------------------------------------------------

provider "docker" {}

# ---------------------------------------------------------------------------
# Coder agent
# ---------------------------------------------------------------------------

resource "coder_agent" "main" {
  arch           = data.coder_provisioner.me.arch
  os             = "linux"
  dir            = "/home/coder/workspace"
  startup_script_behavior = "blocking"

  startup_script = <<-STARTUP
    #!/bin/bash
    set -euo pipefail

    # ── System packages ──────────────────────────────────────────────────────
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
      curl wget git build-essential \
      openssh-client ca-certificates gnupg jq > /dev/null 2>&1

    # ── Node.js ${var.node_version} via NodeSource ───────────────────────────
    curl -fsSL https://deb.nodesource.com/setup_${var.node_version}.x | sudo -E bash - > /dev/null 2>&1
    sudo apt-get install -y -qq nodejs > /dev/null 2>&1

    # ── Corepack + pnpm ─────────────────────────────────────────────────────
    sudo corepack enable
    corepack prepare pnpm@latest --activate 2>/dev/null || sudo npm install -g pnpm

    # ── Global npm packages ─────────────────────────────────────────────────
    sudo npm install -g --silent \
      tsx \
      typescript \
      ts-node \
      eslint \
      prettier \
      @types/node \
      turbo \
      vitest \
      jest \
      nodemon \
      httpie

    # ── Git configuration ────────────────────────────────────────────────────
    git config --global user.name "${data.coder_workspace_owner.me.full_name}"
    git config --global user.email "${data.coder_workspace_owner.me.email}"
    git config --global init.defaultBranch main
    git config --global pull.rebase true
    git config --global credential.helper store

    # Gitea credentials
    cat > ~/.git-credentials <<CRED
    http://omni-admin:omni-admin@omni-gitea:3000
    CRED
    chmod 600 ~/.git-credentials

    # ── SSH key generation ───────────────────────────────────────────────────
    if [ ! -f ~/.ssh/id_ed25519 ]; then
      mkdir -p ~/.ssh
      ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "${data.coder_workspace_owner.me.email}"
      chmod 700 ~/.ssh
      chmod 600 ~/.ssh/id_ed25519
      cat > ~/.ssh/config <<SSHCFG
    Host omni-gitea
      HostName omni-gitea
      Port 2222
      User git
      IdentityFile ~/.ssh/id_ed25519
      StrictHostKeyChecking no
    SSHCFG
      chmod 600 ~/.ssh/config
    fi

    # ── Clone repository if specified ────────────────────────────────────────
    if [ -n "${var.git_repo}" ]; then
      if [ ! -d /home/coder/workspace/.git ]; then
        git clone "${var.git_repo}" /home/coder/workspace
      fi
    fi

    # ── Dotfiles ─────────────────────────────────────────────────────────────
    if [ -n "${var.dotfiles_repo}" ]; then
      coder dotfiles "${var.dotfiles_repo}" --yes 2>/dev/null || true
    fi

    echo "TypeScript development environment ready."
  STARTUP

  metadata {
    display_name = "Node Version"
    key          = "node_version"
    script       = "node --version 2>&1"
    interval     = 3600
    timeout      = 5
  }

  metadata {
    display_name = "npm Version"
    key          = "npm_version"
    script       = "npm --version 2>&1"
    interval     = 3600
    timeout      = 5
  }

  metadata {
    display_name = "pnpm Version"
    key          = "pnpm_version"
    script       = "pnpm --version 2>&1"
    interval     = 3600
    timeout      = 5
  }

  metadata {
    display_name = "Disk Usage"
    key          = "disk_usage"
    script       = "df -h /home/coder | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'"
    interval     = 60
    timeout      = 5
  }

  metadata {
    display_name = "Memory Usage"
    key          = "mem_usage"
    script       = "free -h | awk 'NR==2{printf \"%s/%s (%.1f%%)\\n\", $3, $2, $3/$2*100}'"
    interval     = 30
    timeout      = 5
  }

  metadata {
    display_name = "CPU Load"
    key          = "cpu_load"
    script       = "cat /proc/loadavg | awk '{print $1, $2, $3}'"
    interval     = 30
    timeout      = 5
  }
}

# ---------------------------------------------------------------------------
# VS Code extensions
# ---------------------------------------------------------------------------

resource "coder_app" "code-server" {
  agent_id     = coder_agent.main.id
  slug         = "code-server"
  display_name = "VS Code"
  url          = "http://localhost:13337/?folder=/home/coder/workspace"
  icon         = "/icon/code.svg"
  subdomain    = false
  share        = "owner"
}

resource "coder_script" "vscode_extensions" {
  agent_id     = coder_agent.main.id
  display_name = "Install VS Code Extensions"
  icon         = "/icon/code.svg"
  run_on_start = true
  script       = <<-EXTENSIONS
    #!/bin/bash
    set -euo pipefail
    install_ext() {
      code-server --install-extension "$1" --force > /dev/null 2>&1 || true
    }
    install_ext "dbaeumer.vscode-eslint"
    install_ext "esbenp.prettier-vscode"
    install_ext "ms-vscode.vscode-typescript-next"
    install_ext "bradlc.vscode-tailwindcss"
    install_ext "steoates.autoimport"
    install_ext "eamodio.gitlens"
    install_ext "usernamehw.errorlens"
    install_ext "ms-azuretools.vscode-docker"
    echo "VS Code extensions installed."
  EXTENSIONS
}

# ---------------------------------------------------------------------------
# Persistent volume for /home/coder
# ---------------------------------------------------------------------------

resource "docker_volume" "coder_home" {
  name = "coder-${data.coder_workspace.me.id}-home"

  lifecycle {
    ignore_changes = all
  }

  labels {
    label = "coder.owner"
    value = data.coder_workspace_owner.me.name
  }

  labels {
    label = "coder.owner_id"
    value = data.coder_workspace_owner.me.id
  }

  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }

  labels {
    label = "coder.workspace_name"
    value = data.coder_workspace.me.name
  }

  labels {
    label = "coder.template"
    value = "typescript-dev"
  }
}

# ---------------------------------------------------------------------------
# Docker container — workspace
# ---------------------------------------------------------------------------

resource "docker_image" "workspace" {
  name = "ubuntu:22.04"
}

resource "docker_container" "workspace" {
  count = data.coder_workspace.me.start_count
  name  = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  image = docker_image.workspace.image_id

  env = [
    "CODER_AGENT_TOKEN=${coder_agent.main.token}",
    "CODER_AGENT_URL=${data.coder_workspace.me.access_url}",
  ]

  host {
    host = "host.docker.internal"
    ip   = "host-gateway"
  }

  # Resource limits: 4GB RAM, 2 CPU
  memory  = 4096
  cpu_set = "0-1"

  volumes {
    container_path = "/home/coder"
    volume_name    = docker_volume.coder_home.name
    read_only      = false
  }

  tmpfs = {
    "/tmp" = "rw,noexec,nosuid,size=2g"
  }

  entrypoint = ["sh", "-c", <<-ENTRYPOINT
    #!/bin/bash
    set -eu

    # Create coder user if not exists
    if ! id -u coder > /dev/null 2>&1; then
      useradd -m -s /bin/bash -d /home/coder coder
      echo "coder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/coder
    fi

    # Ensure workspace directory exists
    mkdir -p /home/coder/workspace
    chown -R coder:coder /home/coder

    # Install base dependencies
    apt-get update -qq && apt-get install -y -qq \
      curl sudo git openssh-client ca-certificates > /dev/null 2>&1

    # Install and start code-server
    if ! command -v code-server > /dev/null 2>&1; then
      curl -fsSL https://code-server.dev/install.sh | sh -s -- --method=standalone > /dev/null 2>&1
    fi

    # Start code-server in background
    sudo -u coder code-server --bind-addr 0.0.0.0:13337 --auth none &

    # Download and run the Coder agent
    sudo -u coder --preserve-env=CODER_AGENT_TOKEN,CODER_AGENT_URL bash -c '
      BINARY_DIR=$(mktemp -d)
      curl -fsSL $${CODER_AGENT_URL}/bin/coder-linux-$${CODER_AGENT_ARCH:-amd64} -o $${BINARY_DIR}/coder
      chmod +x $${BINARY_DIR}/coder
      exec $${BINARY_DIR}/coder agent
    '
  ENTRYPOINT
  ]

  networks_advanced {
    name = "omni-quantum-network"
  }

  labels {
    label = "coder.owner"
    value = data.coder_workspace_owner.me.name
  }

  labels {
    label = "coder.owner_id"
    value = data.coder_workspace_owner.me.id
  }

  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }

  labels {
    label = "coder.workspace_name"
    value = data.coder_workspace.me.name
  }

  labels {
    label = "coder.template"
    value = "typescript-dev"
  }

  labels {
    label = "omni.quantum.component"
    value = "coder-workspace"
  }

  labels {
    label = "omni.quantum.tier"
    value = "standard"
  }
}

# ---------------------------------------------------------------------------
# Workspace metadata
# ---------------------------------------------------------------------------

resource "coder_metadata" "workspace_info" {
  count       = data.coder_workspace.me.start_count
  resource_id = docker_container.workspace[0].id

  item {
    key   = "template"
    value = "typescript-dev"
  }

  item {
    key   = "node"
    value = "v${var.node_version}"
  }

  item {
    key   = "resources"
    value = "4GB RAM / 2 CPU / 20GB Disk"
  }

  item {
    key   = "auto_shutdown"
    value = "2h idle"
  }

  item {
    key   = "network"
    value = "omni-quantum-network"
  }
}
