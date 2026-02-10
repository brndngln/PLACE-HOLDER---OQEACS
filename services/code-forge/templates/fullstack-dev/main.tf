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

variable "node_version" {
  description = "Node.js version to install"
  type        = string
  default     = "20"
  validation {
    condition     = contains(["18", "20", "22"], var.node_version)
    error_message = "Supported Node.js versions: 18, 20, 22"
  }
}

variable "go_version" {
  description = "Go version to install"
  type        = string
  default     = "1.22"
  validation {
    condition     = contains(["1.21", "1.22", "1.23"], var.go_version)
    error_message = "Supported Go versions: 1.21, 1.22, 1.23"
  }
}

variable "rust_channel" {
  description = "Rust toolchain channel"
  type        = string
  default     = "stable"
  validation {
    condition     = contains(["stable", "beta", "nightly"], var.rust_channel)
    error_message = "Supported Rust channels: stable, beta, nightly"
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

    # ══════════════════════════════════════════════════════════════════════════
    # System packages
    # ══════════════════════════════════════════════════════════════════════════
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
      software-properties-common curl wget git build-essential \
      libssl-dev libffi-dev zlib1g-dev libbz2-dev libreadline-dev \
      libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev \
      libxmlsec1-dev libgdbm-dev libnss3-dev liblzma-dev \
      openssh-client ca-certificates gnupg jq \
      gcc g++ make pkg-config cmake lldb gdb \
      apt-transport-https lsb-release unzip > /dev/null 2>&1

    # ══════════════════════════════════════════════════════════════════════════
    # Python ${var.python_version}
    # ══════════════════════════════════════════════════════════════════════════
    sudo add-apt-repository -y ppa:deadsnakes/ppa > /dev/null 2>&1
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
      python${var.python_version} \
      python${var.python_version}-venv \
      python${var.python_version}-dev \
      python${var.python_version}-distutils > /dev/null 2>&1

    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${var.python_version} 1
    sudo update-alternatives --set python3 /usr/bin/python${var.python_version}

    curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python${var.python_version}
    sudo python${var.python_version} -m pip install --quiet --upgrade pip setuptools wheel
    sudo python${var.python_version} -m pip install --quiet \
      virtualenv poetry ruff black mypy pytest pytest-cov pytest-asyncio \
      ipython jupyter jupyterlab httpie pre-commit

    poetry config virtualenvs.in-project true

    # ══════════════════════════════════════════════════════════════════════════
    # Node.js ${var.node_version}
    # ══════════════════════════════════════════════════════════════════════════
    curl -fsSL https://deb.nodesource.com/setup_${var.node_version}.x | sudo -E bash - > /dev/null 2>&1
    sudo apt-get install -y -qq nodejs > /dev/null 2>&1

    sudo corepack enable
    corepack prepare pnpm@latest --activate 2>/dev/null || sudo npm install -g pnpm

    sudo npm install -g --silent \
      tsx typescript ts-node eslint prettier \
      @types/node turbo vitest jest nodemon

    # ══════════════════════════════════════════════════════════════════════════
    # Go ${var.go_version}
    # ══════════════════════════════════════════════════════════════════════════
    GO_ARCHIVE="go${var.go_version}.linux-amd64.tar.gz"
    if [ ! -d /usr/local/go ]; then
      curl -fsSL "https://go.dev/dl/$${GO_ARCHIVE}" -o "/tmp/$${GO_ARCHIVE}"
      sudo tar -C /usr/local -xzf "/tmp/$${GO_ARCHIVE}"
      rm -f "/tmp/$${GO_ARCHIVE}"
    fi

    export GOROOT=/usr/local/go
    export GOPATH=/home/coder/go
    export PATH=$${GOPATH}/bin:$${GOROOT}/bin:$${PATH}
    mkdir -p "$${GOPATH}/bin" "$${GOPATH}/src" "$${GOPATH}/pkg"

    go install golang.org/x/tools/gopls@latest
    go install github.com/go-delve/delve/cmd/dlv@latest
    go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
    go install golang.org/x/tools/cmd/goimports@latest
    go install honnef.co/go/tools/cmd/staticcheck@latest
    go install github.com/air-verse/air@latest

    # ══════════════════════════════════════════════════════════════════════════
    # Rust (${var.rust_channel})
    # ══════════════════════════════════════════════════════════════════════════
    if [ ! -d ~/.rustup ]; then
      curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
        sh -s -- -y --default-toolchain ${var.rust_channel} --profile default
    fi
    source "$HOME/.cargo/env"
    rustup default ${var.rust_channel}
    rustup component add clippy rustfmt rust-analyzer rust-src
    cargo install --quiet cargo-watch cargo-edit cargo-nextest sccache 2>/dev/null || true

    mkdir -p ~/.cargo
    cat >> ~/.cargo/config.toml <<'SCCACHE'
    [build]
    rustc-wrapper = "sccache"
    SCCACHE

    # ══════════════════════════════════════════════════════════════════════════
    # Additional CLI tools (Docker CLI, kubectl, psql, redis-cli, mc, HTTPie)
    # ══════════════════════════════════════════════════════════════════════════

    # Docker CLI
    if ! command -v docker > /dev/null 2>&1; then
      curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
      echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
      sudo apt-get update -qq
      sudo apt-get install -y -qq docker-ce-cli > /dev/null 2>&1
    fi

    # kubectl
    if ! command -v kubectl > /dev/null 2>&1; then
      curl -fsSL "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
        -o /tmp/kubectl
      sudo install -o root -g root -m 0755 /tmp/kubectl /usr/local/bin/kubectl
      rm -f /tmp/kubectl
    fi

    # PostgreSQL client
    sudo apt-get install -y -qq postgresql-client > /dev/null 2>&1

    # Redis CLI
    sudo apt-get install -y -qq redis-tools > /dev/null 2>&1

    # MinIO client (mc)
    if ! command -v mc > /dev/null 2>&1; then
      curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /tmp/mc
      sudo install -o root -g root -m 0755 /tmp/mc /usr/local/bin/mc
      rm -f /tmp/mc
    fi

    # Configure mc alias for omni-minio
    mc alias set omni http://omni-minio:9000 minioadmin minioadmin 2>/dev/null || true

    # ══════════════════════════════════════════════════════════════════════════
    # Environment profiles
    # ══════════════════════════════════════════════════════════════════════════
    cat >> ~/.bashrc <<'ENVPROFILE'
    export GOROOT=/usr/local/go
    export GOPATH=/home/coder/go
    export PATH=$GOPATH/bin:$GOROOT/bin:$HOME/.cargo/bin:$PATH
    source "$HOME/.cargo/env" 2>/dev/null || true
    ENVPROFILE

    # ══════════════════════════════════════════════════════════════════════════
    # Git configuration
    # ══════════════════════════════════════════════════════════════════════════
    git config --global user.name "${data.coder_workspace_owner.me.full_name}"
    git config --global user.email "${data.coder_workspace_owner.me.email}"
    git config --global init.defaultBranch main
    git config --global pull.rebase true
    git config --global credential.helper store

    cat > ~/.git-credentials <<CRED
    http://omni-admin:omni-admin@omni-gitea:3000
    CRED
    chmod 600 ~/.git-credentials

    # ══════════════════════════════════════════════════════════════════════════
    # SSH key generation
    # ══════════════════════════════════════════════════════════════════════════
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

    # ══════════════════════════════════════════════════════════════════════════
    # Clone repository if specified
    # ══════════════════════════════════════════════════════════════════════════
    if [ -n "${var.git_repo}" ]; then
      if [ ! -d /home/coder/workspace/.git ]; then
        git clone "${var.git_repo}" /home/coder/workspace
      fi
    fi

    if [ -n "${var.dotfiles_repo}" ]; then
      coder dotfiles "${var.dotfiles_repo}" --yes 2>/dev/null || true
    fi

    echo "Fullstack development environment ready."
    echo "  Python ${var.python_version} | Node ${var.node_version} | Go ${var.go_version} | Rust ${var.rust_channel}"
    echo "  + Docker CLI, kubectl, psql, redis-cli, mc, HTTPie"
  STARTUP

  metadata {
    display_name = "Python Version"
    key          = "python_version"
    script       = "python3 --version 2>&1 | awk '{print $2}'"
    interval     = 3600
    timeout      = 5
  }

  metadata {
    display_name = "Node Version"
    key          = "node_version"
    script       = "node --version 2>&1"
    interval     = 3600
    timeout      = 5
  }

  metadata {
    display_name = "Go Version"
    key          = "go_version"
    script       = "/usr/local/go/bin/go version 2>&1 | awk '{print $3}'"
    interval     = 3600
    timeout      = 5
  }

  metadata {
    display_name = "Rust Version"
    key          = "rust_version"
    script       = "source $HOME/.cargo/env 2>/dev/null; rustc --version 2>&1 | awk '{print $2}'"
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
# VS Code extensions — ALL from all language templates
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

    # Python extensions
    install_ext "ms-python.python"
    install_ext "ms-python.vscode-pylance"
    install_ext "charliermarsh.ruff"

    # TypeScript / JavaScript extensions
    install_ext "dbaeumer.vscode-eslint"
    install_ext "esbenp.prettier-vscode"
    install_ext "ms-vscode.vscode-typescript-next"
    install_ext "bradlc.vscode-tailwindcss"
    install_ext "steoates.autoimport"

    # Go extensions
    install_ext "golang.go"
    install_ext "premparihar.gotestexplorer"
    install_ext "zxh404.vscode-proto3"

    # Rust extensions
    install_ext "rust-lang.rust-analyzer"
    install_ext "serayuzgur.crates"
    install_ext "tamasfe.even-better-toml"
    install_ext "vadimcn.vscode-lldb"

    # Shared extensions
    install_ext "eamodio.gitlens"
    install_ext "usernamehw.errorlens"
    install_ext "ms-azuretools.vscode-docker"
    install_ext "ms-kubernetes-tools.vscode-kubernetes-tools"
    install_ext "cweijan.vscode-postgresql-client2"
    install_ext "rangav.vscode-thunder-client"

    echo "VS Code extensions installed (fullstack)."
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
    value = "fullstack-dev"
  }
}

# ---------------------------------------------------------------------------
# Docker container — workspace (8GB/4CPU/50GB)
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

  # Resource limits: 8GB RAM, 4 CPU
  memory  = 8192
  cpu_set = "0-3"

  volumes {
    container_path = "/home/coder"
    volume_name    = docker_volume.coder_home.name
    read_only      = false
  }

  # Mount Docker socket for Docker-in-Docker operations
  volumes {
    container_path = "/var/run/docker.sock"
    host_path      = "/var/run/docker.sock"
    read_only      = false
  }

  tmpfs = {
    "/tmp" = "rw,noexec,nosuid,size=4g"
  }

  entrypoint = ["sh", "-c", <<-ENTRYPOINT
    #!/bin/bash
    set -eu

    # Create coder user if not exists
    if ! id -u coder > /dev/null 2>&1; then
      useradd -m -s /bin/bash -d /home/coder coder
      echo "coder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/coder
    fi

    # Add coder to docker group if socket exists
    if [ -S /var/run/docker.sock ]; then
      groupadd -f docker 2>/dev/null || true
      usermod -aG docker coder 2>/dev/null || true
      chmod 666 /var/run/docker.sock 2>/dev/null || true
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
    value = "fullstack-dev"
  }

  labels {
    label = "omni.quantum.component"
    value = "coder-workspace"
  }

  labels {
    label = "omni.quantum.tier"
    value = "high"
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
    value = "fullstack-dev"
  }

  item {
    key   = "python"
    value = var.python_version
  }

  item {
    key   = "node"
    value = "v${var.node_version}"
  }

  item {
    key   = "go"
    value = "go${var.go_version}"
  }

  item {
    key   = "rust"
    value = var.rust_channel
  }

  item {
    key   = "resources"
    value = "8GB RAM / 4 CPU / 50GB Disk"
  }

  item {
    key   = "extras"
    value = "Docker CLI, kubectl, psql, redis-cli, mc, HTTPie"
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
