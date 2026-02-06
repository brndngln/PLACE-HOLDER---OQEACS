#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  BUILD CACHE SETUP — Configure Docker BuildKit and cache volumes                   ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

GREEN='\033[0;32m'; NC='\033[0m'
log() { echo -e "${GREEN}[CACHE]${NC} $*"; }

CACHE_ROOT="${CACHE_ROOT:-/var/cache/omni}"

log "Creating cache directories..."
mkdir -p "$CACHE_ROOT"/{pip,npm,yarn,go,cargo,sccache}
chmod 777 "$CACHE_ROOT"/*

log "Configuring Docker for BuildKit..."
DOCKER_CONFIG="${DOCKER_CONFIG:-$HOME/.docker}"
mkdir -p "$DOCKER_CONFIG"

cat > "$DOCKER_CONFIG/daemon.json" << 'EOF'
{
  "features": {
    "buildkit": true
  },
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "20GB"
    }
  }
}
EOF

log "Setting up sccache environment..."
cat >> /etc/environment << 'EOF'
SCCACHE_SERVER=omni-sccache:4226
RUSTC_WRAPPER=sccache
EOF

log "Creating Docker volume for BuildKit cache..."
docker volume create omni-buildkit-cache 2>/dev/null || true

log "Cache setup complete"
log "  Cache root: $CACHE_ROOT"
log "  pip cache: $CACHE_ROOT/pip"
log "  npm cache: $CACHE_ROOT/npm"
log "  go cache: $CACHE_ROOT/go"
log "  cargo cache: $CACHE_ROOT/cargo"
log "  sccache: $CACHE_ROOT/sccache"

log "To use in Dockerfile:"
echo '  RUN --mount=type=cache,target=/root/.cache/pip pip install ...'
echo '  RUN --mount=type=cache,target=/root/.npm npm install ...'
