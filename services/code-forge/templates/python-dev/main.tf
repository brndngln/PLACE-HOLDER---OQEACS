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

variable "python_version" {
  description = "Python version to install"
  type        = string
  default     = "3.12"
  validation {
    condition     = contains(["3.10", "3.11", "3.12"], var.python_version)
    error_message = "Supported Python versions: 3.10, 3.11, 3.12"
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
# Docker provider — connects to the Coder host Docker socket
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
      software-properties-common curl wget git build-essential \
      libssl-dev libffi-dev zlib1g-dev libbz2-dev libreadline-dev \
      libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev \
      libxmlsec1-dev libgdbm-dev libnss3-dev liblzma-dev \
      openssh-client ca-certificates gnupg jq > /dev/null 2>&1

    # ── Python ${var.python_version} via deadsnakes PPA ──────────────────────
    sudo add-apt-repository -y ppa:deadsnakes/ppa > /dev/null 2>&1
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
      python${var.python_version} \
      python${var.python_version}-venv \
      python${var.python_version}-dev \
      python${var.python_version}-distutils > /dev/null 2>&1

    # Set as default python3
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${var.python_version} 1
    sudo update-alternatives --set python3 /usr/bin/python${var.python_version}

    # ── pip, virtualenv, poetry ──────────────────────────────────────────────
    curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python${var.python_version}
    sudo python${var.python_version} -m pip install --quiet --upgrade pip setuptools wheel
    sudo python${var.python_version} -m pip install --quiet \
      virtualenv \
      poetry \
      ruff \
      black \
      mypy \
      pytest \
      pytest-cov \
      pytest-asyncio \
      ipython \
      jupyter \
      jupyterlab \
      httpie \
      pre-commit

    # Symlink pip for convenience
    sudo ln -sf /usr/local/bin/pip${var.python_version} /usr/local/bin/pip 2>/dev/null || true

    # ── Poetry config ────────────────────────────────────────────────────────
    poetry config virtualenvs.in-project true

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

    echo "Python development environment ready."
  STARTUP

  metadata {
    display_name = "Python Version"
    key          = "python_version"
    script       = "python3 --version 2>&1 | awk '{print $2}'"
    interval     = 3600
    timeout      = 5
  }

  metadata {
    display_name = "Poetry Version"
    key          = "poetry_version"
    script       = "poetry --version 2>&1 | awk '{print $3}' | tr -d ')'"
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
    install_ext "ms-python.python"
    install_ext "ms-python.vscode-pylance"
    install_ext "eamodio.gitlens"
    install_ext "usernamehw.errorlens"
    install_ext "charliermarsh.ruff"
    install_ext "esbenp.prettier-vscode"
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
    value = "python-dev"
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

  # 20GB disk limit via tmpfs for workspace scratch space
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
    value = "python-dev"
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
# Auto-shutdown on 2h idle
# ---------------------------------------------------------------------------

resource "coder_metadata" "workspace_info" {
  count       = data.coder_workspace.me.start_count
  resource_id = docker_container.workspace[0].id

  item {
    key   = "template"
    value = "python-dev"
  }

  item {
    key   = "python"
    value = var.python_version
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
