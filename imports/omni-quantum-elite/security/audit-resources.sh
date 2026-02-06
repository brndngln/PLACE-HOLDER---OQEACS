#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  RESOURCE AUDIT — Scan compose files and running containers for limits            ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[AUDIT]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

WORKSPACE="${WORKSPACE:-$(pwd)}"
OUTPUT_DIR="${OUTPUT_DIR:-waves/wave-9-performance/resource-optimization}"
mkdir -p "$OUTPUT_DIR"

# ─────────────────────────────────────────────────────────────────────────────
# Scan docker-compose files
# ─────────────────────────────────────────────────────────────────────────────

log "Scanning docker-compose files for resource limits..."

COMPOSE_FILES=$(find "$WORKSPACE" -name "docker-compose*.yml" -o -name "docker-compose*.yaml" 2>/dev/null | sort)

WITH_LIMITS=()
WITHOUT_LIMITS=()

for f in $COMPOSE_FILES; do
    if grep -qE '^\s*(mem_limit|memory|cpus|cpu_quota|deploy:)' "$f" 2>/dev/null; then
        WITH_LIMITS+=("$f")
    else
        WITHOUT_LIMITS+=("$f")
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "COMPOSE FILE RESOURCE AUDIT"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "WITH resource limits (${#WITH_LIMITS[@]}):"
for f in "${WITH_LIMITS[@]:-}"; do
    echo "  ✅ $f"
done
echo ""
echo "WITHOUT resource limits (${#WITHOUT_LIMITS[@]}):"
for f in "${WITHOUT_LIMITS[@]:-}"; do
    echo "  ⚠️  $f"
done

# ─────────────────────────────────────────────────────────────────────────────
# Audit running containers
# ─────────────────────────────────────────────────────────────────────────────

if command -v docker &> /dev/null && docker ps &> /dev/null; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "RUNNING CONTAINER ACTUAL USAGE"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}"
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "RECOMMENDED LIMITS (usage × 1.5 headroom)"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    docker stats --no-stream --format "{{.Name}},{{.MemUsage}}" | while IFS=',' read -r name mem; do
        # Extract numeric memory value
        mem_val=$(echo "$mem" | grep -oE '^[0-9.]+' | head -1)
        mem_unit=$(echo "$mem" | grep -oE '[A-Za-z]+' | head -1)
        
        if [[ -n "$mem_val" ]]; then
            recommended=$(echo "$mem_val * 1.5" | bc 2>/dev/null || echo "$mem_val")
            echo "  $name: ${recommended}${mem_unit:-MiB}"
        fi
    done
fi

# ─────────────────────────────────────────────────────────────────────────────
# Generate report
# ─────────────────────────────────────────────────────────────────────────────

REPORT="${OUTPUT_DIR}/resource-audit-$(date +%Y%m%d).md"

{
    echo "# Resource Audit Report"
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo ""
    echo "## Compose Files"
    echo ""
    echo "### With Resource Limits (${#WITH_LIMITS[@]})"
    for f in "${WITH_LIMITS[@]:-}"; do
        echo "- \`$f\`"
    done
    echo ""
    echo "### Without Resource Limits (${#WITHOUT_LIMITS[@]})"
    for f in "${WITHOUT_LIMITS[@]:-}"; do
        echo "- \`$f\` ⚠️"
    done
    echo ""
    echo "## Recommendations"
    echo ""
    echo "Apply limits from \`optimized-limits.yml\` to all services."
} > "$REPORT"

log "Audit report: $REPORT"
