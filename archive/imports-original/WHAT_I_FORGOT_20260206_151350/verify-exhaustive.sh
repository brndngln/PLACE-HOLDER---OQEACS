#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# ⚛ OMNI QUANTUM ELITE — Tier 4: Exhaustive Verification Runner (Nightly)
# ══════════════════════════════════════════════════════════════════════════════
# All checks that are too slow for CI but essential for long-term quality.
# Runs on a nightly cron schedule. Results go to Grafana + Mattermost.
#
# Sub-checks:
#   1. Fuzz testing (Atheris/Hypothesis for Python, AFL++ for C)
#   2. Mutation testing (mutmut for Python, Stryker for JS/TS)
#   3. Full vulnerability scan (Trivy + Grype + OSV-Scanner)
#   4. License compliance (ScanCode + licensee)
#   5. Technical debt quantification (wily + vulture + churn)
#   6. Dead code detection (vulture)
#
# Usage:
#   verify-exhaustive --all
#   verify-exhaustive --fuzz --time 300          # 5-min fuzz campaign
#   verify-exhaustive --mutation --timeout 600   # 10-min mutation budget
#   verify-exhaustive --vulnscan                 # Vulnerability scan only
#   verify-exhaustive --license                  # License compliance only
#   verify-exhaustive --techdebt                 # Tech debt + dead code only
#   verify-exhaustive --json                     # JSON-only output
#
# Environment:
#   WORKSPACE           Project root (default: /workspace)
#   FUZZ_DURATION        Fuzz campaign seconds (default: 300)
#   MUTATION_TIMEOUT     Mutation test timeout (default: 600)
#   REPORT_URL           POST report JSON here (optional)
#   MATTERMOST_WEBHOOK   Mattermost webhook URL (optional)
#   GRAFANA_URL          Grafana push URL for metrics (optional)
#   TRIVY_SEVERITY       Trivy severity filter (default: CRITICAL,HIGH)
#   LICENSE_ALLOWLIST    Comma-separated allowed licenses
# ══════════════════════════════════════════════════════════════════════════════
set -uo pipefail

readonly REPORT_FILE="/tmp/verify-exhaustive-report.json"
readonly VERSION="1.0.0"
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly NC='\033[0m'
readonly BOLD='\033[1m'

RESULTS_DIR=$(mktemp -d)
WORKSPACE="${WORKSPACE:-/workspace}"
FUZZ_DURATION="${FUZZ_DURATION:-300}"
MUTATION_TIMEOUT="${MUTATION_TIMEOUT:-600}"
REPORT_URL="${REPORT_URL:-}"
MATTERMOST_WEBHOOK="${MATTERMOST_WEBHOOK:-}"
GRAFANA_URL="${GRAFANA_URL:-}"
TRIVY_SEVERITY="${TRIVY_SEVERITY:-CRITICAL,HIGH}"
LICENSE_ALLOWLIST="${LICENSE_ALLOWLIST:-MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause,ISC,Python-2.0,PSF-2.0,Unlicense,CC0-1.0,0BSD}"
RUN_MODE="all"
JSON_ONLY=false
START_TIME=$(date +%s%N)
TOTAL_CHECKS=0
TOTAL_FAILURES=0
TOTAL_WARNINGS=0

# ─── Helpers ────────────────────────────────────────────────────────────────

elapsed_ms() { echo $(( ($(date +%s%N) - START_TIME) / 1000000 )); }

log_header() {
    [[ "$JSON_ONLY" == "false" ]] && echo -e "\n${BOLD}${CYAN}═══ $1 ═══${NC}"
}

log_pass() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    [[ "$JSON_ONLY" == "false" ]] && echo -e "  ${GREEN}✓${NC} $1"
}

log_fail() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    TOTAL_FAILURES=$((TOTAL_FAILURES + 1))
    [[ "$JSON_ONLY" == "false" ]] && echo -e "  ${RED}✗${NC} $1"
}

log_warn() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    [[ "$JSON_ONLY" == "false" ]] && echo -e "  ${YELLOW}⚠${NC} $1"
}

log_info() {
    [[ "$JSON_ONLY" == "false" ]] && echo -e "  ${CYAN}ℹ${NC} $1"
}

write_result() {
    local check="$1" status="$2" details="$3" duration_ms="$4"
    local findings="${5:-[]}" suggestions="${6:-[]}"
    cat > "${RESULTS_DIR}/${check}.json" <<EOF
{
  "check": "${check}",
  "status": "${status}",
  "details": ${details},
  "findings": ${findings},
  "suggestions": ${suggestions},
  "duration_ms": ${duration_ms}
}
EOF
}

# ─── Parse Arguments ────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)        RUN_MODE="all"; shift ;;
        --fuzz)       RUN_MODE="fuzz"; shift ;;
        --mutation)   RUN_MODE="mutation"; shift ;;
        --vulnscan)   RUN_MODE="vulnscan"; shift ;;
        --license)    RUN_MODE="license"; shift ;;
        --techdebt)   RUN_MODE="techdebt"; shift ;;
        --json)       JSON_ONLY=true; shift ;;
        --time)       FUZZ_DURATION="$2"; shift 2 ;;
        --timeout)    MUTATION_TIMEOUT="$2"; shift 2 ;;
        --workspace)  WORKSPACE="$2"; shift 2 ;;
        *)            echo "Unknown option: $1"; exit 1 ;;
    esac
done

cd "$WORKSPACE" || { echo "Workspace not found: $WORKSPACE"; exit 1; }

if [[ "$JSON_ONLY" == "false" ]]; then
    echo -e "${BOLD}${MAGENTA}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║  ⚛ OMNI QUANTUM ELITE — Tier 4: Exhaustive Nightly Verification ║"
    echo "║  Fuzz | Mutation | VulnScan | License | TechDebt               ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
fi


# ═════════════════════════════════════════════════════════════════════════════
# CHECK 1: Fuzz Testing
# ═════════════════════════════════════════════════════════════════════════════

run_fuzz() {
    log_header "Fuzz Testing (${FUZZ_DURATION}s campaign)"
    local start_ms=$(date +%s%N)

    # Look for fuzz targets
    local fuzz_targets
    fuzz_targets=$(find "$WORKSPACE" -name "fuzz_*.py" -o -name "*_fuzz.py" 2>/dev/null | head -20)

    # Also check for hypothesis property tests
    local hypothesis_tests
    hypothesis_tests=$(find "$WORKSPACE" -name "test_*.py" -exec grep -l "@given\|@hypothesis" {} \; 2>/dev/null | head -20)

    local atheris_count=0
    local hypothesis_count=0
    local crashes=0
    local total_inputs=0

    if [[ -n "$fuzz_targets" ]]; then
        log_info "Found Atheris fuzz targets"
        atheris_count=$(echo "$fuzz_targets" | wc -l)

        # Run each fuzz target with time limit
        local per_target_time=$((FUZZ_DURATION / (atheris_count + 1)))
        [[ "$per_target_time" -lt 10 ]] && per_target_time=10

        while IFS= read -r target; do
            local target_name=$(basename "$target" .py)
            log_info "Fuzzing: ${target_name} (${per_target_time}s)..."

            local corpus_dir="/tmp/fuzz-corpus-${target_name}"
            local crash_dir="/tmp/fuzz-crashes-${target_name}"
            mkdir -p "$corpus_dir" "$crash_dir"

            # Run with timeout
            timeout "${per_target_time}" python "$target" \
                "$corpus_dir" \
                -artifact_prefix="$crash_dir/" \
                -max_total_time="$per_target_time" \
                -print_final_stats=1 \
                2>/tmp/fuzz-${target_name}.log || true

            # Count crashes
            local target_crashes
            target_crashes=$(find "$crash_dir" -name "crash-*" -o -name "oom-*" -o -name "timeout-*" 2>/dev/null | wc -l)
            crashes=$((crashes + target_crashes))

            # Count total inputs
            local target_inputs
            target_inputs=$(grep -oP 'stat::number_of_executed_units:\s*\K\d+' /tmp/fuzz-${target_name}.log 2>/dev/null || echo 0)
            total_inputs=$((total_inputs + target_inputs))

            if [[ "$target_crashes" -gt 0 ]]; then
                log_fail "Fuzz target ${target_name}: ${target_crashes} crashes found"
            else
                log_pass "Fuzz target ${target_name}: clean (${target_inputs} inputs)"
            fi
        done <<< "$fuzz_targets"
    fi

    if [[ -n "$hypothesis_tests" ]]; then
        log_info "Running Hypothesis property tests..."
        hypothesis_count=$(echo "$hypothesis_tests" | wc -l)

        local hyp_output="/tmp/hypothesis-output.txt"
        python -m pytest \
            -x \
            --timeout=60 \
            -m "hypothesis or property" \
            --hypothesis-seed=0 \
            --hypothesis-show-statistics \
            $hypothesis_tests \
            2>&1 | tee "$hyp_output" || true

        local hyp_failures
        hyp_failures=$(grep -c "FAILED" "$hyp_output" 2>/dev/null || echo 0)
        crashes=$((crashes + hyp_failures))

        if [[ "$hyp_failures" -gt 0 ]]; then
            log_fail "Hypothesis: ${hyp_failures} property test failures"
        else
            log_pass "Hypothesis: all property tests passed"
        fi
    fi

    if [[ "$atheris_count" -eq 0 ]] && [[ "$hypothesis_count" -eq 0 ]]; then
        log_warn "No fuzz targets or property tests found"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "fuzz" "skip" '"No fuzz targets found"' "$dur" '[]' \
            '["Create fuzz_*.py files with Atheris targets for critical parsers", "Add @hypothesis.given() property tests for data processing functions"]'
        return
    fi

    local status="pass"
    [[ "$crashes" -gt 0 ]] && status="fail"

    local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
    write_result "fuzz" "$status" "{
        \"atheris_targets\": ${atheris_count},
        \"hypothesis_files\": ${hypothesis_count},
        \"total_inputs_tested\": ${total_inputs},
        \"crashes_found\": ${crashes},
        \"campaign_duration_s\": ${FUZZ_DURATION}
    }" "$dur"
}

# ═════════════════════════════════════════════════════════════════════════════
# CHECK 2: Mutation Testing
# ═════════════════════════════════════════════════════════════════════════════

run_mutation() {
    log_header "Mutation Testing (${MUTATION_TIMEOUT}s budget)"
    local start_ms=$(date +%s%N)

    local has_python=false
    local has_js=false

    [[ -n "$(find "$WORKSPACE" -name "*.py" -not -path "*/venv/*" -not -path "*/__pycache__/*" | head -1)" ]] && has_python=true
    [[ -n "$(find "$WORKSPACE" -name "*.js" -o -name "*.ts" -not -path "*/node_modules/*" | head -1)" ]] && has_js=true

    local total_mutants=0
    local killed=0
    local survived=0
    local timeout_count=0
    local mutation_score=0

    if [[ "$has_python" == "true" ]]; then
        log_info "Running mutmut (Python mutation testing)..."

        # Check for test files first
        local test_files
        test_files=$(find "$WORKSPACE" -name "test_*.py" -not -path "*/venv/*" | head -5)

        if [[ -z "$test_files" ]]; then
            log_warn "No Python test files found for mutation testing"
        else
            # Run mutmut with timeout
            timeout "${MUTATION_TIMEOUT}" mutmut run \
                --paths-to-mutate="$(find "$WORKSPACE" -name "*.py" -not -name "test_*" -not -path "*/venv/*" -not -path "*/__pycache__/*" -not -path "*/migrations/*" | head -20 | tr '\n' ',')" \
                --runner="python -m pytest -x -q --timeout=30" \
                --no-progress \
                2>/tmp/mutmut.log || true

            # Get results
            local mutmut_results="/tmp/mutmut-results.txt"
            mutmut results 2>/dev/null > "$mutmut_results" || true

            if [[ -f "$mutmut_results" ]]; then
                total_mutants=$(grep -oP 'Mutants:\s*\K\d+' "$mutmut_results" 2>/dev/null || echo 0)
                killed=$(grep -oP 'killed:\s*\K\d+' "$mutmut_results" 2>/dev/null || echo 0)
                survived=$(grep -oP 'survived:\s*\K\d+' "$mutmut_results" 2>/dev/null || echo 0)
                timeout_count=$(grep -oP 'timeout:\s*\K\d+' "$mutmut_results" 2>/dev/null || echo 0)
            fi

            # Also try JSON output
            mutmut junitxml > /tmp/mutmut-junit.xml 2>/dev/null || true

            if [[ "$total_mutants" -gt 0 ]]; then
                mutation_score=$(python3 -c "print(round(($killed / $total_mutants) * 100, 1))" 2>/dev/null || echo 0)
                log_info "Python: ${killed}/${total_mutants} mutants killed (${mutation_score}%)"
            fi
        fi
    fi

    local js_mutation_score=0
    if [[ "$has_js" == "true" ]] && [[ -f "$WORKSPACE/package.json" ]]; then
        log_info "Running Stryker (JS/TS mutation testing)..."

        # Check for Stryker config or create minimal one
        if [[ ! -f "$WORKSPACE/stryker.config.mjs" ]] && [[ ! -f "$WORKSPACE/stryker.conf.js" ]]; then
            # Auto-detect test runner
            local test_runner="jest"
            if grep -q "vitest" "$WORKSPACE/package.json" 2>/dev/null; then
                test_runner="vitest"
            fi

            cat > /tmp/stryker.config.mjs <<STRYKER
/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
  testRunner: '${test_runner}',
  reporters: ['json', 'clear-text'],
  jsonReporter: { fileName: '/tmp/stryker-report.json' },
  timeoutMS: 10000,
  concurrency: 2,
};
STRYKER
            local stryker_config="/tmp/stryker.config.mjs"
        else
            local stryker_config="$WORKSPACE/stryker.config.mjs"
            [[ -f "$WORKSPACE/stryker.conf.js" ]] && stryker_config="$WORKSPACE/stryker.conf.js"
        fi

        timeout "${MUTATION_TIMEOUT}" npx stryker run "$stryker_config" 2>/tmp/stryker.log || true

        if [[ -f "/tmp/stryker-report.json" ]]; then
            local js_killed js_survived js_total
            js_total=$(jq '.files | [.[].mutants[]] | length' /tmp/stryker-report.json 2>/dev/null || echo 0)
            js_killed=$(jq '.files | [.[].mutants[] | select(.status == "Killed")] | length' /tmp/stryker-report.json 2>/dev/null || echo 0)
            js_survived=$(jq '.files | [.[].mutants[] | select(.status == "Survived")] | length' /tmp/stryker-report.json 2>/dev/null || echo 0)

            total_mutants=$((total_mutants + js_total))
            killed=$((killed + js_killed))
            survived=$((survived + js_survived))

            if [[ "$js_total" -gt 0 ]]; then
                js_mutation_score=$(python3 -c "print(round(($js_killed / $js_total) * 100, 1))" 2>/dev/null || echo 0)
                log_info "JS/TS: ${js_killed}/${js_total} mutants killed (${js_mutation_score}%)"
            fi
        fi
    fi

    if [[ "$total_mutants" -eq 0 ]]; then
        log_warn "No mutation tests executed"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "mutation" "skip" '"No test files found for mutation testing"' "$dur" '[]' \
            '["Add unit tests to enable mutation testing", "Mutation score > 80% indicates strong test suite"]'
        return
    fi

    local combined_score=0
    [[ "$total_mutants" -gt 0 ]] && combined_score=$(python3 -c "print(round(($killed / $total_mutants) * 100, 1))" 2>/dev/null || echo 0)

    local status="pass"
    if python3 -c "exit(0 if float('$combined_score') < 60 else 1)" 2>/dev/null; then
        log_fail "Mutation score: ${combined_score}% (< 60% threshold)"
        status="fail"
    elif python3 -c "exit(0 if float('$combined_score') < 80 else 1)" 2>/dev/null; then
        log_warn "Mutation score: ${combined_score}% (< 80% target)"
        status="warn"
    else
        log_pass "Mutation score: ${combined_score}%"
    fi

    local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
    write_result "mutation" "$status" "{
        \"total_mutants\": ${total_mutants},
        \"killed\": ${killed},
        \"survived\": ${survived},
        \"timeouts\": ${timeout_count},
        \"mutation_score_percent\": ${combined_score},
        \"python_score\": ${mutation_score},
        \"js_score\": ${js_mutation_score}
    }" "$dur"
}

# ═════════════════════════════════════════════════════════════════════════════
# CHECK 3: Full Vulnerability Scan (Trivy + Grype + OSV-Scanner)
# ═════════════════════════════════════════════════════════════════════════════

run_vulnscan() {
    log_header "Full Vulnerability Scan (3 scanners)"
    local start_ms=$(date +%s%N)

    local total_critical=0
    local total_high=0
    local total_medium=0
    local total_low=0
    local scanner_results="[]"

    # ── Trivy ───────────────────────────────────────────────────────────────
    log_info "Running Trivy filesystem scan..."
    local trivy_json="/tmp/trivy-results.json"

    trivy fs "$WORKSPACE" \
        --format json \
        --output "$trivy_json" \
        --severity "$TRIVY_SEVERITY" \
        --skip-dirs "node_modules,venv,.git,.venv,__pycache__" \
        --scanners vuln,secret,misconfig \
        2>/dev/null || true

    if [[ -f "$trivy_json" ]]; then
        local trivy_critical trivy_high trivy_medium trivy_low
        trivy_critical=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "$trivy_json" 2>/dev/null || echo 0)
        trivy_high=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "$trivy_json" 2>/dev/null || echo 0)
        trivy_medium=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM")] | length' "$trivy_json" 2>/dev/null || echo 0)
        trivy_low=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity == "LOW")] | length' "$trivy_json" 2>/dev/null || echo 0)

        total_critical=$((total_critical + trivy_critical))
        total_high=$((total_high + trivy_high))
        total_medium=$((total_medium + trivy_medium))
        total_low=$((total_low + trivy_low))

        local trivy_total=$((trivy_critical + trivy_high + trivy_medium + trivy_low))
        log_info "Trivy: ${trivy_total} vulns (${trivy_critical}C/${trivy_high}H/${trivy_medium}M/${trivy_low}L)"

        # Count misconfigs and secrets
        local misconfigs secrets
        misconfigs=$(jq '[.Results[]?.Misconfigurations[]?] | length' "$trivy_json" 2>/dev/null || echo 0)
        secrets=$(jq '[.Results[]?.Secrets[]?] | length' "$trivy_json" 2>/dev/null || echo 0)
        [[ "$misconfigs" -gt 0 ]] && log_info "Trivy: ${misconfigs} misconfigurations"
        [[ "$secrets" -gt 0 ]] && log_fail "Trivy: ${secrets} secrets detected!"

        scanner_results=$(echo "$scanner_results" | jq ". + [{
            \"scanner\": \"trivy\",
            \"critical\": ${trivy_critical}, \"high\": ${trivy_high},
            \"medium\": ${trivy_medium}, \"low\": ${trivy_low},
            \"misconfigs\": ${misconfigs}, \"secrets\": ${secrets}
        }]")
    fi

    # ── Grype ───────────────────────────────────────────────────────────────
    log_info "Running Grype scan..."
    local grype_json="/tmp/grype-results.json"

    grype dir:"$WORKSPACE" \
        --output json \
        --file "$grype_json" \
        2>/dev/null || true

    if [[ -f "$grype_json" ]]; then
        local grype_critical grype_high grype_medium grype_low
        grype_critical=$(jq '[.matches[] | select(.vulnerability.severity == "Critical")] | length' "$grype_json" 2>/dev/null || echo 0)
        grype_high=$(jq '[.matches[] | select(.vulnerability.severity == "High")] | length' "$grype_json" 2>/dev/null || echo 0)
        grype_medium=$(jq '[.matches[] | select(.vulnerability.severity == "Medium")] | length' "$grype_json" 2>/dev/null || echo 0)
        grype_low=$(jq '[.matches[] | select(.vulnerability.severity == "Low")] | length' "$grype_json" 2>/dev/null || echo 0)

        local grype_total=$((grype_critical + grype_high + grype_medium + grype_low))
        log_info "Grype: ${grype_total} vulns (${grype_critical}C/${grype_high}H/${grype_medium}M/${grype_low}L)"

        # Use max of scanners for deduplication
        [[ "$grype_critical" -gt "$total_critical" ]] && total_critical=$grype_critical
        [[ "$grype_high" -gt "$total_high" ]] && total_high=$grype_high

        scanner_results=$(echo "$scanner_results" | jq ". + [{
            \"scanner\": \"grype\",
            \"critical\": ${grype_critical}, \"high\": ${grype_high},
            \"medium\": ${grype_medium}, \"low\": ${grype_low}
        }]")
    fi

    # ── OSV-Scanner ─────────────────────────────────────────────────────────
    log_info "Running OSV-Scanner..."
    local osv_json="/tmp/osv-results.json"

    osv-scanner --format json --recursive "$WORKSPACE" > "$osv_json" 2>/dev/null || true

    if [[ -f "$osv_json" ]] && [[ -s "$osv_json" ]]; then
        local osv_vulns
        osv_vulns=$(jq '.results | [.[].packages[].vulnerabilities[]] | length' "$osv_json" 2>/dev/null || echo 0)
        log_info "OSV-Scanner: ${osv_vulns} advisories"

        scanner_results=$(echo "$scanner_results" | jq ". + [{
            \"scanner\": \"osv-scanner\",
            \"advisories\": ${osv_vulns}
        }]")
    fi

    # ── Verdict ─────────────────────────────────────────────────────────────
    local status="pass"
    if [[ "$total_critical" -gt 0 ]]; then
        log_fail "VulnScan: ${total_critical} CRITICAL vulnerabilities"
        status="fail"
    elif [[ "$total_high" -gt 5 ]]; then
        log_fail "VulnScan: ${total_high} HIGH vulnerabilities"
        status="fail"
    elif [[ "$total_high" -gt 0 ]]; then
        log_warn "VulnScan: ${total_high} HIGH vulnerabilities"
        status="warn"
    else
        log_pass "VulnScan: No critical/high vulnerabilities"
    fi

    local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
    write_result "vulnscan" "$status" "{
        \"critical\": ${total_critical},
        \"high\": ${total_high},
        \"medium\": ${total_medium},
        \"low\": ${total_low},
        \"scanners\": ${scanner_results}
    }" "$dur"
}

# ═════════════════════════════════════════════════════════════════════════════
# CHECK 4: License Compliance
# ═════════════════════════════════════════════════════════════════════════════

run_license() {
    log_header "License Compliance"
    local start_ms=$(date +%s%N)

    IFS=',' read -ra ALLOWED_LICENSES <<< "$LICENSE_ALLOWLIST"

    local violations=0
    local total_packages=0
    local unknown_licenses=0
    local violation_details="[]"

    # ── Python licenses ─────────────────────────────────────────────────────
    if [[ -f "$WORKSPACE/requirements.txt" ]] || [[ -f "$WORKSPACE/pyproject.toml" ]]; then
        log_info "Checking Python package licenses..."

        # Use pip-licenses if available, or fallback to ScanCode
        if pip install pip-licenses --quiet --break-system-packages 2>/dev/null; then
            local pip_licenses="/tmp/pip-licenses.json"
            pip-licenses --format=json --output-file="$pip_licenses" 2>/dev/null || true

            if [[ -f "$pip_licenses" ]]; then
                total_packages=$(jq '. | length' "$pip_licenses" 2>/dev/null || echo 0)

                while IFS= read -r line; do
                    local pkg_name pkg_license
                    pkg_name=$(echo "$line" | jq -r '.Name' 2>/dev/null)
                    pkg_license=$(echo "$line" | jq -r '.License' 2>/dev/null)

                    if [[ "$pkg_license" == "UNKNOWN" ]] || [[ -z "$pkg_license" ]]; then
                        unknown_licenses=$((unknown_licenses + 1))
                        continue
                    fi

                    # Check against allowlist
                    local allowed=false
                    for al in "${ALLOWED_LICENSES[@]}"; do
                        if echo "$pkg_license" | grep -qi "$al"; then
                            allowed=true
                            break
                        fi
                    done

                    if [[ "$allowed" == "false" ]]; then
                        violations=$((violations + 1))
                        violation_details=$(echo "$violation_details" | jq ". + [{
                            \"package\": \"${pkg_name}\",
                            \"license\": \"${pkg_license}\",
                            \"ecosystem\": \"python\"
                        }]")
                    fi
                done < <(jq -c '.[]' "$pip_licenses" 2>/dev/null)

                log_info "Python: ${total_packages} packages, ${violations} violations, ${unknown_licenses} unknown"
            fi
        fi
    fi

    # ── Node.js licenses ────────────────────────────────────────────────────
    if [[ -f "$WORKSPACE/package.json" ]] && [[ -d "$WORKSPACE/node_modules" ]]; then
        log_info "Checking Node.js package licenses..."

        local npm_licenses="/tmp/npm-licenses.json"
        npx license-checker --json --production --out "$npm_licenses" 2>/dev/null || true

        if [[ -f "$npm_licenses" ]]; then
            local npm_count
            npm_count=$(jq 'keys | length' "$npm_licenses" 2>/dev/null || echo 0)
            total_packages=$((total_packages + npm_count))

            while IFS= read -r key; do
                local npm_license
                npm_license=$(jq -r ".[\"${key}\"].licenses // \"UNKNOWN\"" "$npm_licenses" 2>/dev/null)

                if [[ "$npm_license" == "UNKNOWN" ]]; then
                    unknown_licenses=$((unknown_licenses + 1))
                    continue
                fi

                local allowed=false
                for al in "${ALLOWED_LICENSES[@]}"; do
                    if echo "$npm_license" | grep -qi "$al"; then
                        allowed=true
                        break
                    fi
                done

                if [[ "$allowed" == "false" ]]; then
                    violations=$((violations + 1))
                    violation_details=$(echo "$violation_details" | jq ". + [{
                        \"package\": \"${key}\",
                        \"license\": \"${npm_license}\",
                        \"ecosystem\": \"npm\"
                    }]")
                fi
            done < <(jq -r 'keys[]' "$npm_licenses" 2>/dev/null)

            log_info "Node.js: ${npm_count} packages checked"
        fi
    fi

    # ── Project license check ───────────────────────────────────────────────
    log_info "Checking project license..."
    local project_license="UNKNOWN"
    if command -v licensee &>/dev/null; then
        project_license=$(licensee detect "$WORKSPACE" 2>/dev/null | grep "License:" | head -1 | awk '{print $2}' || echo "UNKNOWN")
    fi
    [[ "$project_license" == "UNKNOWN" ]] && [[ -f "$WORKSPACE/LICENSE" ]] && project_license="present (undetected)"

    local status="pass"
    if [[ "$violations" -gt 0 ]]; then
        log_fail "License: ${violations} packages with non-allowed licenses"
        status="fail"
    elif [[ "$unknown_licenses" -gt 10 ]]; then
        log_warn "License: ${unknown_licenses} packages with unknown licenses"
        status="warn"
    else
        log_pass "License: All ${total_packages} packages compliant"
    fi

    local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
    write_result "license" "$status" "{
        \"total_packages\": ${total_packages},
        \"violations\": ${violations},
        \"unknown_licenses\": ${unknown_licenses},
        \"project_license\": \"${project_license}\",
        \"allowlist\": \"${LICENSE_ALLOWLIST}\",
        \"violation_details\": ${violation_details}
    }" "$dur"
}

# ═════════════════════════════════════════════════════════════════════════════
# CHECK 5: Technical Debt Quantification
# ═════════════════════════════════════════════════════════════════════════════

run_techdebt() {
    log_header "Technical Debt Analysis"
    local start_ms=$(date +%s%N)

    local dead_code_count=0
    local todo_count=0
    local fixme_count=0
    local hack_count=0
    local total_loc=0
    local test_loc=0
    local test_ratio=0

    # ── Dead Code Detection (Vulture) ───────────────────────────────────────
    log_info "Scanning for dead code (Vulture)..."
    local vulture_output="/tmp/vulture-output.txt"
    vulture "$WORKSPACE" \
        --min-confidence 80 \
        --exclude "test_*,*_test.py,conftest.py,venv,node_modules,.git,migrations" \
        > "$vulture_output" 2>/dev/null || true

    dead_code_count=$(wc -l < "$vulture_output" 2>/dev/null || echo 0)
    dead_code_count=$((dead_code_count > 0 ? dead_code_count : 0))

    local dead_code_findings="[]"
    if [[ "$dead_code_count" -gt 0 ]]; then
        dead_code_findings=$(head -20 "$vulture_output" | jq -Rs 'split("\n") | map(select(length > 0))')
        log_info "Dead code: ${dead_code_count} unused definitions found"
    else
        log_pass "Dead code: none detected"
    fi

    # ── TODO/FIXME/HACK Count ───────────────────────────────────────────────
    log_info "Counting technical debt markers..."
    todo_count=$(grep -rn "TODO\|todo" "$WORKSPACE" --include="*.py" --include="*.js" --include="*.ts" --include="*.go" --include="*.rs" 2>/dev/null | grep -v node_modules | grep -v venv | grep -v __pycache__ | wc -l || echo 0)
    fixme_count=$(grep -rn "FIXME\|fixme" "$WORKSPACE" --include="*.py" --include="*.js" --include="*.ts" --include="*.go" --include="*.rs" 2>/dev/null | grep -v node_modules | grep -v venv | wc -l || echo 0)
    hack_count=$(grep -rn "HACK\|hack\|XXX\|WORKAROUND" "$WORKSPACE" --include="*.py" --include="*.js" --include="*.ts" 2>/dev/null | grep -v node_modules | grep -v venv | wc -l || echo 0)

    local debt_markers=$((todo_count + fixme_count + hack_count))
    log_info "Debt markers: ${todo_count} TODO, ${fixme_count} FIXME, ${hack_count} HACK/XXX"

    # ── Lines of Code & Test Ratio ──────────────────────────────────────────
    log_info "Calculating code metrics..."
    total_loc=$(find "$WORKSPACE" \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.go" -o -name "*.rs" \) \
        -not -path "*/node_modules/*" -not -path "*/venv/*" -not -path "*/__pycache__/*" -not -path "*/.git/*" \
        -exec cat {} \; 2>/dev/null | wc -l || echo 0)

    test_loc=$(find "$WORKSPACE" \( -name "test_*.py" -o -name "*_test.py" -o -name "*.test.js" -o -name "*.test.ts" -o -name "*.spec.js" -o -name "*.spec.ts" \) \
        -not -path "*/node_modules/*" -not -path "*/venv/*" \
        -exec cat {} \; 2>/dev/null | wc -l || echo 0)

    if [[ "$total_loc" -gt 0 ]]; then
        test_ratio=$(python3 -c "print(round(($test_loc / $total_loc) * 100, 1))" 2>/dev/null || echo 0)
    fi

    log_info "LOC: ${total_loc} source, ${test_loc} test (${test_ratio}% ratio)"

    # ── Wily Complexity Trends (if git history available) ───────────────────
    local complexity_trend="stable"
    if [[ -d "$WORKSPACE/.git" ]]; then
        log_info "Analyzing complexity trends..."
        cd "$WORKSPACE"
        wily build . --max-revisions 10 2>/dev/null || true

        local wily_report="/tmp/wily-report.json"
        wily report --format json . 2>/dev/null > "$wily_report" || true

        if [[ -f "$wily_report" ]] && [[ -s "$wily_report" ]]; then
            # Simple trend: compare latest vs earliest complexity
            complexity_trend="analyzed"
        fi
        cd - >/dev/null
    fi

    # ── Verdict ─────────────────────────────────────────────────────────────
    local status="pass"
    local suggestions='["Keep monitoring technical debt trends"]'

    if [[ "$dead_code_count" -gt 50 ]]; then
        log_fail "Tech debt: ${dead_code_count} dead code items"
        status="fail"
        suggestions='["Remove unused functions/classes/imports identified by Vulture", "Run: vulture --min-confidence 90 to see high-confidence dead code only"]'
    elif [[ "$debt_markers" -gt 50 ]]; then
        log_warn "Tech debt: ${debt_markers} TODO/FIXME/HACK markers"
        status="warn"
        suggestions='["Address FIXME items first (likely bugs)", "Schedule TODO items into project tracker", "Replace HACK/XXX with proper implementations"]'
    elif [[ "$dead_code_count" -gt 20 ]] || [[ "$debt_markers" -gt 20 ]]; then
        log_warn "Tech debt: moderate (${dead_code_count} dead code, ${debt_markers} markers)"
        status="warn"
    else
        log_pass "Tech debt: low (${dead_code_count} dead code, ${debt_markers} markers)"
    fi

    local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
    write_result "techdebt" "$status" "{
        \"dead_code_count\": ${dead_code_count},
        \"todo_count\": ${todo_count},
        \"fixme_count\": ${fixme_count},
        \"hack_count\": ${hack_count},
        \"total_debt_markers\": ${debt_markers},
        \"total_loc\": ${total_loc},
        \"test_loc\": ${test_loc},
        \"test_ratio_percent\": ${test_ratio},
        \"complexity_trend\": \"${complexity_trend}\"
    }" "$dur" "$dead_code_findings" "$suggestions"
}


# ═════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION
# ═════════════════════════════════════════════════════════════════════════════

case "$RUN_MODE" in
    all)
        run_fuzz
        run_mutation
        run_vulnscan
        run_license
        run_techdebt
        ;;
    fuzz)     run_fuzz ;;
    mutation) run_mutation ;;
    vulnscan) run_vulnscan ;;
    license)  run_license ;;
    techdebt) run_techdebt ;;
esac


# ═════════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ═════════════════════════════════════════════════════════════════════════════

TOTAL_MS=$(elapsed_ms)

CHECKS="[]"
for f in "${RESULTS_DIR}"/*.json; do
    [[ -f "$f" ]] || continue
    CHECKS=$(echo "$CHECKS" | jq --slurpfile item "$f" '. + $item')
done

FINAL_STATUS="pass"
[[ "$TOTAL_FAILURES" -gt 0 ]] && FINAL_STATUS="fail"
[[ "$TOTAL_WARNINGS" -gt 0 ]] && [[ "$FINAL_STATUS" != "fail" ]] && FINAL_STATUS="warn"

cat > "$REPORT_FILE" <<EOF
{
  "tier": 4,
  "tier_name": "exhaustive",
  "version": "${VERSION}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "workspace": "${WORKSPACE}",
  "duration_ms": ${TOTAL_MS},
  "status": "${FINAL_STATUS}",
  "summary": {
    "total_checks": ${TOTAL_CHECKS},
    "failures": ${TOTAL_FAILURES},
    "warnings": ${TOTAL_WARNINGS},
    "passed": $((TOTAL_CHECKS - TOTAL_FAILURES - TOTAL_WARNINGS))
  },
  "checks": ${CHECKS}
}
EOF

# Send to Mattermost
if [[ -n "$MATTERMOST_WEBHOOK" ]]; then
    local emoji="✅"
    [[ "$FINAL_STATUS" == "warn" ]] && emoji="⚠️"
    [[ "$FINAL_STATUS" == "fail" ]] && emoji="❌"

    curl -sf -X POST "$MATTERMOST_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "{
            \"channel\": \"quality\",
            \"text\": \"${emoji} **Nightly Exhaustive Verification: ${FINAL_STATUS^^}**\nChecks: ${TOTAL_CHECKS} | Failures: ${TOTAL_FAILURES} | Warnings: ${TOTAL_WARNINGS} | Duration: ${TOTAL_MS}ms\",
            \"username\": \"omni-verify\"
        }" &>/dev/null || true
fi

# Post report if URL configured
if [[ -n "$REPORT_URL" ]]; then
    curl -sf -X POST "$REPORT_URL" \
        -H "Content-Type: application/json" \
        -d @"$REPORT_FILE" &>/dev/null || true
fi

# Print summary
if [[ "$JSON_ONLY" == "true" ]]; then
    cat "$REPORT_FILE"
else
    echo ""
    echo -e "${BOLD}═══ Nightly Exhaustive Summary ═══${NC}"
    echo -e "  Duration: ${TOTAL_MS}ms"
    echo -e "  Checks:   ${TOTAL_CHECKS} total"
    echo -e "  Passed:   $((TOTAL_CHECKS - TOTAL_FAILURES - TOTAL_WARNINGS))"
    echo -e "  Warnings: ${TOTAL_WARNINGS}"
    echo -e "  Failures: ${TOTAL_FAILURES}"
    echo -e "  Status:   $(
        if [[ "$FINAL_STATUS" == "pass" ]]; then echo -e "${GREEN}PASS${NC}";
        elif [[ "$FINAL_STATUS" == "warn" ]]; then echo -e "${YELLOW}WARN${NC}";
        else echo -e "${RED}FAIL${NC}"; fi
    )"
    echo -e "  Report:   ${REPORT_FILE}"
    echo ""
fi

rm -rf "$RESULTS_DIR"

[[ "$FINAL_STATUS" == "fail" ]] && exit 1 || exit 0
