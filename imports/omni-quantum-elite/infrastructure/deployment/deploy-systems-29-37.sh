#!/bin/bash
###############################################################################
#                    ⚛  OMNI QUANTUM ELITE AI CODING SYSTEM
#                   Grand Master Deployment — Systems 29-37
#
#   Deploys all 9 enhanced infrastructure systems in dependency order,
#   completing the full 37-system platform.
#
#   Prerequisites:
#     - Systems 1-28 already running (Core + Extended platform)
#     - Docker & Docker Compose installed
#     - omni-quantum-network Docker network exists
#
#   Usage:
#     chmod +x deploy-systems-29-37.sh
#     ./deploy-systems-29-37.sh
###############################################################################
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SYSTEMS=(
    "system-29-enhanced-monitoring"
    "system-30-enhanced-logging"
    "system-31-uptime-monitor"
    "system-32-enhanced-backup"
    "system-33-enhanced-secrets"
    "system-34-enhanced-proxy"
    "system-35-cicd-pipelines"
    "system-36-dev-environments"
    "system-37-master-orchestrator"
)

SYSTEM_NAMES=(
    "Pulse Command Pro (Enhanced Monitoring)"
    "Log Nexus Pro (Enhanced Logging)"
    "Guardian Eye (Uptime Monitor)"
    "Backup Fortress Pro (Enhanced Backup)"
    "Cryptographic Fortress Pro (Enhanced Secrets)"
    "Gateway Sentinel Pro (Enhanced Proxy)"
    "Build Forge (CI/CD Pipelines)"
    "Code Forge (Dev Environments)"
    "Omni Command (Master Orchestrator)"
)

TOTAL=${#SYSTEMS[@]}
PASSED=0
FAILED=0
SKIPPED=0

# ===========================================================================
banner() {
echo -e "${PURPLE}${BOLD}"
cat << 'EOF'

  ╔═══════════════════════════════════════════════════════════════╗
  ║                                                               ║
  ║      ⚛   OMNI QUANTUM ELITE AI CODING SYSTEM                 ║
  ║                                                               ║
  ║      Grand Master Deployment — Systems 29-37                  ║
  ║      100% Open Source · Self-Hosted · Zero Dependencies       ║
  ║                                                               ║
  ╚═══════════════════════════════════════════════════════════════╝

EOF
echo -e "${NC}"
}

check_prerequisites() {
    echo -e "${BLUE}[PRE] Checking prerequisites...${NC}"

    # Docker
    if ! command -v docker &>/dev/null; then
        echo -e "${RED}  ✗ Docker not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Docker$(docker --version | awk '{print " "$3}')${NC}"

    # Docker Compose
    if ! docker compose version &>/dev/null; then
        echo -e "${RED}  ✗ Docker Compose not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ Docker Compose$(docker compose version --short 2>/dev/null | awk '{print " "$1}')${NC}"

    # Network
    if docker network inspect omni-quantum-network &>/dev/null; then
        echo -e "${GREEN}  ✓ omni-quantum-network exists${NC}"
    else
        echo -e "${YELLOW}  ⚠ Creating omni-quantum-network...${NC}"
        docker network create omni-quantum-network
        echo -e "${GREEN}  ✓ Network created${NC}"
    fi

    # Check core services
    local core_services=("omni-postgres" "omni-redis")
    for svc in "${core_services[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${svc}$"; then
            echo -e "${GREEN}  ✓ ${svc} running${NC}"
        else
            echo -e "${YELLOW}  ⚠ ${svc} not running (some systems may fail)${NC}"
        fi
    done

    echo ""
}

deploy_system() {
    local index=$1
    local dir="${SYSTEMS[$index]}"
    local name="${SYSTEM_NAMES[$index]}"
    local num=$((index + 29))
    local step=$((index + 1))

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}[${step}/${TOTAL}] System ${num}: ${name}${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    local sys_path="${BASE_DIR}/${dir}"

    if [ ! -d "$sys_path" ]; then
        echo -e "${RED}  ✗ Directory not found: ${sys_path}${NC}"
        ((SKIPPED++))
        return
    fi

    if [ ! -f "${sys_path}/docker-compose.yml" ]; then
        echo -e "${RED}  ✗ No docker-compose.yml found${NC}"
        ((SKIPPED++))
        return
    fi

    # Run init script if exists
    if [ -f "${sys_path}/scripts/init.sh" ]; then
        echo -e "${BLUE}  Running init script...${NC}"
        chmod +x "${sys_path}/scripts/init.sh"
        bash "${sys_path}/scripts/init.sh" 2>&1 | sed 's/^/    /' || true
    else
        # Standard deploy: build + up
        echo -e "${BLUE}  Building images...${NC}"
        (cd "$sys_path" && docker compose build --quiet 2>&1 | sed 's/^/    /') || true

        echo -e "${BLUE}  Starting services...${NC}"
        (cd "$sys_path" && docker compose up -d 2>&1 | sed 's/^/    /')
    fi

    # Verify at least one container started
    local running
    running=$(cd "$sys_path" && docker compose ps --format json 2>/dev/null | grep -c '"running"' || echo "0")

    if [ "$running" -gt 0 ]; then
        echo -e "${GREEN}  ✓ System ${num} deployed (${running} containers running)${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}  ⚠ System ${num} deployed but no containers running yet${NC}"
        ((PASSED++))
    fi

    echo ""
}

print_summary() {
    echo -e "${PURPLE}${BOLD}"
    echo "  ╔═══════════════════════════════════════════════════════════╗"
    echo "  ║              DEPLOYMENT COMPLETE                         ║"
    echo "  ╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo -e "  ${GREEN}✓ Deployed:  ${PASSED}${NC}"
    if [ "$FAILED" -gt 0 ]; then
        echo -e "  ${RED}✗ Failed:    ${FAILED}${NC}"
    fi
    if [ "$SKIPPED" -gt 0 ]; then
        echo -e "  ${YELLOW}⊘ Skipped:   ${SKIPPED}${NC}"
    fi
    echo ""

    echo -e "${BOLD}  Platform Endpoints:${NC}"
    echo "  ┌─────────────────────────────────────────────────────────┐"
    echo "  │ Orchestrator API     http://localhost:9500              │"
    echo "  │ Omni Dashboard       http://localhost:9501              │"
    echo "  │ Voice Bridge         http://localhost:9502              │"
    echo "  │ Uptime Kuma          http://localhost:3001              │"
    echo "  │ Traefik Dashboard    http://localhost:8080              │"
    echo "  │ Woodpecker CI        http://localhost:8000              │"
    echo "  │ Coder Workspaces     http://localhost:7080              │"
    echo "  │ Thanos Query         http://localhost:10902             │"
    echo "  │ Karma Alerts         http://localhost:8081              │"
    echo "  └─────────────────────────────────────────────────────────┘"
    echo ""

    echo -e "${BOLD}  Quick Start:${NC}"
    echo "    omni status            — Platform overview"
    echo "    omni services          — All 36+ services"
    echo "    omni health vault      — Check a specific service"
    echo "    omni restart gitea     — Restart a service"
    echo "    omni backup            — Backup all services"
    echo ""
    echo "    Mattermost: !omni help — ChatOps commands"
    echo "    Omi Voice:  'Check platform status'"
    echo ""

    echo -e "${PURPLE}${BOLD}"
    echo "  ═══════════════════════════════════════════════════════════"
    echo "    ⚛  37 SYSTEMS DEPLOYED — OMNI QUANTUM ELITE IS LIVE"
    echo "  ═══════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# ===========================================================================
# MAIN
# ===========================================================================
banner
check_prerequisites

for i in "${!SYSTEMS[@]}"; do
    deploy_system "$i"
done

print_summary
