#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="${1:-/root/.ssh/brendan_authorized_key}"
USER_NAME="brendan"

id -u "$USER_NAME" >/dev/null 2>&1 || useradd -m -s /bin/bash -G docker,sudo "$USER_NAME"
passwd -l "$USER_NAME" >/dev/null 2>&1 || true

if [[ ! -f "$KEY_PATH" ]]; then
  echo "Public key not found at $KEY_PATH" >&2
  exit 1
fi

install -d -m 700 -o "$USER_NAME" -g "$USER_NAME" "/home/${USER_NAME}/.ssh"
install -m 600 -o "$USER_NAME" -g "$USER_NAME" "$KEY_PATH" "/home/${USER_NAME}/.ssh/authorized_keys"

cat >/etc/ssh/sshd_config.d/99-omni-vscode.conf <<CONF
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers brendan
ClientAliveInterval 60
ClientAliveCountMax 10
AllowTcpForwarding yes
GatewayPorts no
CONF

apt-get update
apt-get install -y python3 python3-pip nodejs npm golang-go rustc cargo docker.io postgresql-client redis-tools curl jq yq httpie bat fd-find ripgrep fzf htop tmux
python3 -m pip install --break-system-packages httpx rich || true

mkdir -p /home/brendan/.omni/bin /home/brendan/projects
ln -sfn /opt/omni-quantum/repos /home/brendan/repos
ln -sfn /opt/omni-quantum /home/brendan/platform
cp -f services/code-forge/templates/omni-command/home-config/.omni/aliases.sh /home/brendan/.omni/aliases.sh
cp -f services/code-forge/templates/omni-command/home-config/.omni/env.sh /home/brendan/.omni/env.sh
cp -f scripts/infrastructure/home-config/.omni/cli.py /home/brendan/.omni/cli.py
ln -sfn /home/brendan/.omni/cli.py /home/brendan/.omni/bin/omni
chown -R brendan:brendan /home/brendan/.omni /home/brendan/projects

if ! grep -q ".omni/env.sh" /home/brendan/.bashrc; then
  cat >> /home/brendan/.bashrc <<'BASHRC'
source /home/brendan/.omni/env.sh
source /home/brendan/.omni/aliases.sh
export PATH="$HOME/.omni/bin:$HOME/.local/bin:$PATH"
BASHRC
fi

systemctl restart sshd || systemctl restart ssh
su - brendan -c "curl -sf http://omni-orchestrator:9500/api/v1/overview | jq .status" >/dev/null
echo "✅ VS Code Remote SSH configured for user brendan"
