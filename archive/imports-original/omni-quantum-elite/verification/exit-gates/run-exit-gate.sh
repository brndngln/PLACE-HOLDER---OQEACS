#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  WAVE 9 EXIT GATE — Performance & Scale Validation                                 ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; NC='\033[0m'
pass() { echo -e "${GREEN}✅ PASS${NC} $*"; PASS_COUNT=$((PASS_COUNT+1)); }
fail() { echo -e "${RED}❌ FAIL${NC} $*"; FAIL_COUNT=$((FAIL_COUNT+1)); }
log() { echo -e "${YELLOW}[CHECK]${NC} $*"; }

PASS_COUNT=0
FAIL_COUNT=0

echo "═══════════════════════════════════════════════════════════════"
echo "WAVE 9 EXIT GATE — Performance & Scale"
echo "═══════════════════════════════════════════════════════════════"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WAVE_DIR="$(dirname "$SCRIPT_DIR")"

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 1: Semantic Cache Health
# ─────────────────────────────────────────────────────────────────────────────
log "1) Semantic Cache health check"
if curl -sf http://omni-semantic-cache:8380/health > /dev/null 2>&1; then
    pass "Semantic cache healthy (:8380)"
else
    fail "Semantic cache not responding"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 2: Cache Hit Test
# ─────────────────────────────────────────────────────────────────────────────
log "2) Semantic cache hit test"
PROMPT='{"model":"test","messages":[{"role":"user","content":"What is 2+2?"}]}'
T1=$(date +%s%3N)
curl -sf -X POST http://omni-semantic-cache:8380/api/v1/chat \
    -H "Content-Type: application/json" -d "$PROMPT" > /dev/null 2>&1 || true
T2=$(date +%s%3N)
FIRST_MS=$((T2 - T1))

T3=$(date +%s%3N)
RESP=$(curl -sf -X POST http://omni-semantic-cache:8380/api/v1/chat \
    -H "Content-Type: application/json" -d "$PROMPT" 2>/dev/null || echo '{}')
T4=$(date +%s%3N)
SECOND_MS=$((T4 - T3))

if echo "$RESP" | grep -q '"hit": true' && [[ "$SECOND_MS" -lt "$FIRST_MS" ]]; then
    pass "Cache hit detected (${SECOND_MS}ms < ${FIRST_MS}ms)"
else
    fail "Cache hit not detected or second request not faster"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 3: PgBouncer Health
# ─────────────────────────────────────────────────────────────────────────────
log "3) PgBouncer connection test"
if pg_isready -h omni-pgbouncer -p 6432 > /dev/null 2>&1; then
    pass "PgBouncer accepting connections (:6432)"
else
    fail "PgBouncer not responding"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 4: Docker Compose YAML Validation
# ─────────────────────────────────────────────────────────────────────────────
log "4) Docker Compose YAML validation"
COMPOSE_FILES=$(find "$WAVE_DIR" -name "docker-compose.yml" -o -name "docker-compose.yaml" 2>/dev/null)
VALID=0
INVALID=0
for f in $COMPOSE_FILES; do
    if python3 -c "import yaml; yaml.safe_load(open('$f'))" 2>/dev/null; then
        VALID=$((VALID+1))
    else
        INVALID=$((INVALID+1))
        echo "  Invalid: $f"
    fi
done
if [[ "$INVALID" -eq 0 ]]; then
    pass "All $VALID docker-compose files are valid YAML"
else
    fail "$INVALID invalid docker-compose files"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 5: Grafana Dashboard JSON
# ─────────────────────────────────────────────────────────────────────────────
log "5) Grafana dashboard JSON validation"
DASHBOARD="$WAVE_DIR/cost-tracking/grafana-dashboard.json"
if [[ -f "$DASHBOARD" ]] && jq . "$DASHBOARD" > /dev/null 2>&1; then
    pass "Cost tracking Grafana dashboard is valid JSON"
else
    fail "Grafana dashboard invalid or missing"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 6: Resource Limits Coverage
# ─────────────────────────────────────────────────────────────────────────────
log "6) Resource limits coverage"
LIMITS_FILE="$WAVE_DIR/resource-optimization/optimized-limits.yml"
if [[ -f "$LIMITS_FILE" ]]; then
    SERVICE_COUNT=$(grep -c "omni-" "$LIMITS_FILE" 2>/dev/null || echo "0")
    if [[ "$SERVICE_COUNT" -ge 30 ]]; then
        pass "Resource limits cover $SERVICE_COUNT services (≥30)"
    else
        fail "Resource limits only cover $SERVICE_COUNT services (<30)"
    fi
else
    fail "optimized-limits.yml not found"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 7: Parallel Pipeline Tiers
# ─────────────────────────────────────────────────────────────────────────────
log "7) Parallel pipeline tier configuration"
PIPELINE_FILE="$WAVE_DIR/parallelization/parallel-pipeline.yml"
if [[ -f "$PIPELINE_FILE" ]]; then
    TIER_COUNT=$(grep -c "group: tier" "$PIPELINE_FILE" 2>/dev/null || echo "0")
    if [[ "$TIER_COUNT" -ge 3 ]]; then
        pass "Pipeline has $TIER_COUNT parallel tier groups (≥3)"
    else
        fail "Pipeline only has $TIER_COUNT tier groups (<3)"
    fi
else
    fail "parallel-pipeline.yml not found"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 8: Profiler Docker Image
# ─────────────────────────────────────────────────────────────────────────────
log "8) Profiler Docker image build test"
PROFILER_DIR="$(dirname "$WAVE_DIR")/../docker-images/omni-profiler"
if [[ -d "$PROFILER_DIR" ]]; then
    if docker build -q "$PROFILER_DIR" > /dev/null 2>&1; then
        pass "Profiler Docker image builds successfully"
    else
        fail "Profiler Docker image build failed"
    fi
else
    fail "Profiler directory not found"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "RESULTS: $PASS_COUNT passed, $FAIL_COUNT failed"
echo "═══════════════════════════════════════════════════════════════"

if [[ "$FAIL_COUNT" -eq 0 ]]; then
    echo -e "${GREEN}🎉 WAVE 9 EXIT GATE PASSED${NC}"
    exit 0
else
    echo -e "${RED}💥 WAVE 9 EXIT GATE FAILED${NC}"
    exit 1
fi
