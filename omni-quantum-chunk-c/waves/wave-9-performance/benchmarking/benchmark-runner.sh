#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  BENCHMARK RUNNER — pytest-benchmark + hyperfine + k6                              ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[BENCHMARK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

OUTPUT_FILE="${OUTPUT_FILE:-benchmark-results.json}"
BASELINE_FILE="${BASELINE_FILE:-benchmark-baseline.json}"
REGRESSION_THRESHOLD_LATENCY="${REGRESSION_THRESHOLD_LATENCY:-10}"  # percent
REGRESSION_THRESHOLD_THROUGHPUT="${REGRESSION_THRESHOLD_THROUGHPUT:-5}"  # percent

RESULTS=()
REGRESSIONS=()

# ─────────────────────────────────────────────────────────────────────────────
# Python benchmarks (pytest-benchmark)
# ─────────────────────────────────────────────────────────────────────────────

run_pytest_benchmarks() {
    log "Running pytest-benchmark..."
    
    if [[ -d "tests/benchmarks" ]]; then
        pytest tests/benchmarks \
            --benchmark-json=pytest-bench.json \
            --benchmark-disable-gc \
            --benchmark-warmup=on \
            --benchmark-min-rounds=5 \
            || warn "pytest-benchmark failed"
        
        if [[ -f pytest-bench.json ]]; then
            # Extract key metrics
            python3 << 'PYEOF'
import json
with open('pytest-bench.json') as f:
    data = json.load(f)
for bench in data.get('benchmarks', []):
    name = bench['name']
    mean_ns = bench['stats']['mean'] * 1e9
    print(f"  {name}: {mean_ns:.2f}ns (mean)")
PYEOF
        fi
    else
        log "No pytest benchmarks found at tests/benchmarks/"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# CLI benchmarks (hyperfine)
# ─────────────────────────────────────────────────────────────────────────────

run_cli_benchmarks() {
    log "Running CLI benchmarks with hyperfine..."
    
    if command -v hyperfine &> /dev/null; then
        # Example: benchmark common CLI tools
        hyperfine \
            --warmup 3 \
            --min-runs 10 \
            --export-json hyperfine-bench.json \
            'echo "test"' \
            'python -c "print(1)"' \
            || warn "hyperfine failed"
    else
        log "hyperfine not installed, skipping CLI benchmarks"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# HTTP benchmarks (k6 or wrk)
# ─────────────────────────────────────────────────────────────────────────────

run_http_benchmarks() {
    log "Running HTTP benchmarks..."
    
    TARGET_URL="${BENCHMARK_TARGET_URL:-http://localhost:8000/health}"
    
    if command -v k6 &> /dev/null; then
        k6 run --out json=k6-bench.json - << 'K6SCRIPT'
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
    vus: 10,
    duration: '30s',
    thresholds: {
        http_req_duration: ['p(95)<500'],
        http_req_failed: ['rate<0.01'],
    },
};

export default function () {
    let res = http.get(__ENV.TARGET_URL || 'http://localhost:8000/health');
    check(res, {
        'status is 200': (r) => r.status === 200,
        'latency < 500ms': (r) => r.timings.duration < 500,
    });
    sleep(0.1);
}
K6SCRIPT
    elif command -v wrk &> /dev/null; then
        wrk -t4 -c100 -d30s "$TARGET_URL" > wrk-bench.txt 2>&1 || warn "wrk failed"
    else
        log "Neither k6 nor wrk installed, skipping HTTP benchmarks"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Regression detection
# ─────────────────────────────────────────────────────────────────────────────

check_regressions() {
    log "Checking for regressions against baseline..."
    
    if [[ ! -f "$BASELINE_FILE" ]]; then
        log "No baseline found at $BASELINE_FILE, skipping regression check"
        return 0
    fi
    
    python3 << PYEOF
import json
import sys

LATENCY_THRESHOLD = ${REGRESSION_THRESHOLD_LATENCY}
THROUGHPUT_THRESHOLD = ${REGRESSION_THRESHOLD_THROUGHPUT}

try:
    with open('${BASELINE_FILE}') as f:
        baseline = json.load(f)
    with open('${OUTPUT_FILE}') as f:
        current = json.load(f)
except Exception as e:
    print(f"Could not load benchmark files: {e}")
    sys.exit(0)

regressions = []

for name, base_val in baseline.get('latency_p95', {}).items():
    curr_val = current.get('latency_p95', {}).get(name, base_val)
    change = ((curr_val - base_val) / base_val) * 100 if base_val else 0
    if change > LATENCY_THRESHOLD:
        regressions.append(f"LATENCY REGRESSION: {name} +{change:.1f}% (threshold: {LATENCY_THRESHOLD}%)")

for name, base_val in baseline.get('throughput', {}).items():
    curr_val = current.get('throughput', {}).get(name, base_val)
    change = ((base_val - curr_val) / base_val) * 100 if base_val else 0
    if change > THROUGHPUT_THRESHOLD:
        regressions.append(f"THROUGHPUT REGRESSION: {name} -{change:.1f}% (threshold: {THROUGHPUT_THRESHOLD}%)")

if regressions:
    print("⚠️  REGRESSIONS DETECTED:")
    for r in regressions:
        print(f"  - {r}")
    sys.exit(1)
else:
    print("✅ No regressions detected")
    sys.exit(0)
PYEOF
}

# ─────────────────────────────────────────────────────────────────────────────
# Alert on regression
# ─────────────────────────────────────────────────────────────────────────────

send_alert() {
    local message="$1"
    
    if [[ -n "${MATTERMOST_WEBHOOK_URL:-}" ]]; then
        curl -s -X POST "$MATTERMOST_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"🚨 **Benchmark Regression**\n${message}\"}" || true
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

log "Starting benchmark suite..."

run_pytest_benchmarks
run_cli_benchmarks
run_http_benchmarks

# Aggregate results
python3 << PYEOF
import json
import os

results = {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "commit": os.getenv("CI_COMMIT_SHA", "unknown")[:8],
    "latency_p95": {},
    "throughput": {},
    "benchmarks": []
}

# Merge pytest results
if os.path.exists('pytest-bench.json'):
    with open('pytest-bench.json') as f:
        data = json.load(f)
    for b in data.get('benchmarks', []):
        results['benchmarks'].append({
            "name": b['name'],
            "mean_ns": b['stats']['mean'] * 1e9,
            "stddev_ns": b['stats']['stddev'] * 1e9,
        })
        results['latency_p95'][b['name']] = b['stats']['mean'] * 1e9

with open('${OUTPUT_FILE}', 'w') as f:
    json.dump(results, f, indent=2)

print(f"Results written to ${OUTPUT_FILE}")
PYEOF

# Check for regressions
if ! check_regressions; then
    send_alert "Benchmark regressions detected in commit ${CI_COMMIT_SHA:-unknown}"
    exit 1
fi

log "Benchmark suite complete"
