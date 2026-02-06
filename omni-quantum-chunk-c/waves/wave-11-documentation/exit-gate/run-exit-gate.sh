#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  WAVE 11 EXIT GATE — Documentation & Polish                                        ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'
pass() { echo -e "${GREEN}✅ PASS${NC} $*"; PASS_COUNT=$((PASS_COUNT+1)); }
fail() { echo -e "${RED}❌ FAIL${NC} $*"; FAIL_COUNT=$((FAIL_COUNT+1)); }
log() { echo -e "${YELLOW}[CHECK]${NC} $*"; }

PASS_COUNT=0
FAIL_COUNT=0

echo "═══════════════════════════════════════════════════════════════"
echo "WAVE 11 EXIT GATE — Documentation & Polish"
echo "═══════════════════════════════════════════════════════════════"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WAVE_DIR="$(dirname "$SCRIPT_DIR")"

# Check all documentation files exist
log "1) API Documentation Generator"
[[ -f "$WAVE_DIR/api-docs/generate-openapi.py" ]] && pass "API docs generator exists" || fail "API docs generator missing"

log "2) Architecture Diagrams"
[[ -f "$WAVE_DIR/architecture/system-overview.mermaid" ]] && pass "System overview diagram exists" || fail "System overview missing"
[[ -f "$WAVE_DIR/architecture/data-flow.mermaid" ]] && pass "Data flow diagram exists" || fail "Data flow missing"

log "3) Runbook Collection"
[[ -f "$WAVE_DIR/runbooks/index.md" ]] && pass "Runbooks exist" || fail "Runbooks missing"

log "4) Configuration Reference"
[[ -f "$WAVE_DIR/config-reference/environment-variables.md" ]] && pass "Config reference exists" || fail "Config reference missing"

log "5) Troubleshooting Guide"
[[ -f "$WAVE_DIR/troubleshooting/common-issues.md" ]] && pass "Troubleshooting guide exists" || fail "Troubleshooting missing"

log "6) Quick Start Guide"
[[ -f "$WAVE_DIR/quick-start/README.md" ]] && pass "Quick start guide exists" || fail "Quick start missing"

log "7) Contributing Guidelines"
[[ -f "$WAVE_DIR/contributing/CONTRIBUTING.md" ]] && pass "Contributing guidelines exist" || fail "Contributing missing"

log "8) Changelog"
[[ -f "$WAVE_DIR/changelog/CHANGELOG.md" ]] && pass "Changelog exists" || fail "Changelog missing"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "RESULTS: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "═══════════════════════════════════════════════════════════════"

if [[ "$FAIL_COUNT" -eq 0 ]]; then
    echo -e "${GREEN}🎉 WAVE 11 EXIT GATE PASSED${NC}"
    exit 0
else
    echo -e "${RED}💥 WAVE 11 EXIT GATE FAILED${NC}"
    exit 1
fi
