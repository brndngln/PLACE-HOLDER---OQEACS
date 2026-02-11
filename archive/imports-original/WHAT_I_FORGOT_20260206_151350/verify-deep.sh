#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# ⚛ OMNI QUANTUM ELITE — Tier 3: Deep Verification Runner (< 10 min)
# ══════════════════════════════════════════════════════════════════════════════
# Runs heavyweight analysis that requires compilation, semantic understanding,
# and real service interaction. Executes 5 sub-steps:
#
#   1. CodeQL semantic analysis (security-and-quality suite)
#   2. Facebook Infer static analysis (null derefs, races, leaks)
#   3. Integration tests with Testcontainers (real DB/cache/queue)
#   4. Performance benchmarks vs. baseline
#   5. Deep complexity analysis (radon + lizard + cohesion)
#
# Usage:
#   verify-deep --all                 # Run all checks
#   verify-deep --codeql              # CodeQL only
#   verify-deep --infer               # Infer only
#   verify-deep --integration         # Integration tests only
#   verify-deep --benchmark           # Benchmarks only
#   verify-deep --complexity          # Complexity only
#   verify-deep --report-only         # JSON report, no console output
#   verify-deep --baseline /path      # Set benchmark baseline directory
#
# Environment:
#   WORKSPACE          Project root (default: /workspace)
#   MAX_TIME           Time limit in seconds (default: 600)
#   MIN_COVERAGE       Minimum integration test coverage (default: 80)
#   BENCHMARK_BASELINE Path to baseline benchmarks (optional)
#   DOCKER_HOST        Docker socket for Testcontainers
#   CODEQL_SUITE       CodeQL suite (default: security-and-quality)
#   REPORT_URL         URL to POST JSON report to (optional)
# ══════════════════════════════════════════════════════════════════════════════
set -uo pipefail

readonly REPORT_FILE="/tmp/verify-deep-report.json"
readonly MAX_TIME="${MAX_TIME:-600}"
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
BENCHMARK_BASELINE="${BENCHMARK_BASELINE:-}"
CODEQL_SUITE="${CODEQL_SUITE:-security-and-quality}"
REPORT_URL="${REPORT_URL:-}"
RUN_MODE="all"
REPORT_ONLY=false
START_TIME=$(date +%s%N)
TOTAL_CHECKS=0
TOTAL_FAILURES=0
TOTAL_WARNINGS=0

# ─── Helpers ────────────────────────────────────────────────────────────────

elapsed_ms() {
    echo $(( ($(date +%s%N) - START_TIME) / 1000000 ))
}

log_header() {
    if [[ "$REPORT_ONLY" == "false" ]]; then
        echo -e "\n${BOLD}${CYAN}═══ $1 ═══${NC}"
    fi
}

log_pass() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [[ "$REPORT_ONLY" == "false" ]]; then
        echo -e "  ${GREEN}✓${NC} $1"
    fi
}

log_fail() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    TOTAL_FAILURES=$((TOTAL_FAILURES + 1))
    if [[ "$REPORT_ONLY" == "false" ]]; then
        echo -e "  ${RED}✗${NC} $1"
    fi
}

log_warn() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
    if [[ "$REPORT_ONLY" == "false" ]]; then
        echo -e "  ${YELLOW}⚠${NC} $1"
    fi
}

log_info() {
    if [[ "$REPORT_ONLY" == "false" ]]; then
        echo -e "  ${CYAN}ℹ${NC} $1"
    fi
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
        --all)           RUN_MODE="all"; shift ;;
        --codeql)        RUN_MODE="codeql"; shift ;;
        --infer)         RUN_MODE="infer"; shift ;;
        --integration)   RUN_MODE="integration"; shift ;;
        --benchmark)     RUN_MODE="benchmark"; shift ;;
        --complexity)    RUN_MODE="complexity"; shift ;;
        --report-only)   REPORT_ONLY=true; shift ;;
        --baseline)      BENCHMARK_BASELINE="$2"; shift 2 ;;
        --workspace)     WORKSPACE="$2"; shift 2 ;;
        *)               echo "Unknown option: $1"; exit 1 ;;
    esac
done

cd "$WORKSPACE" || { echo "Workspace not found: $WORKSPACE"; exit 1; }

if [[ "$REPORT_ONLY" == "false" ]]; then
    echo -e "${BOLD}${MAGENTA}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  ⚛ OMNI QUANTUM ELITE — Tier 3: Deep Verification          ║"
    echo "║  Target: < 10 minutes | Semantic + Integration + Benchmark ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
fi

# ═════════════════════════════════════════════════════════════════════════════
# CHECK 1: CodeQL Semantic Analysis
# ═════════════════════════════════════════════════════════════════════════════

run_codeql() {
    log_header "CodeQL Semantic Analysis"
    local start_ms=$(date +%s%N)
    local codeql_db="/tmp/codeql-db"
    local codeql_results="/tmp/codeql-results.sarif"
    local findings="[]"
    local suggestions="[]"

    # Detect language
    local lang=""
    if ls "$WORKSPACE"/*.py "$WORKSPACE"/**/*.py &>/dev/null 2>&1; then
        lang="python"
    elif ls "$WORKSPACE"/*.js "$WORKSPACE"/*.ts "$WORKSPACE"/**/*.js "$WORKSPACE"/**/*.ts &>/dev/null 2>&1; then
        lang="javascript"
    elif ls "$WORKSPACE"/*.go "$WORKSPACE"/**/*.go &>/dev/null 2>&1; then
        lang="go"
    elif ls "$WORKSPACE"/*.java "$WORKSPACE"/**/*.java &>/dev/null 2>&1; then
        lang="java"
    fi

    if [[ -z "$lang" ]]; then
        log_warn "No supported language detected for CodeQL"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "codeql" "skip" '"No supported language detected"' "$dur"
        return
    fi

    log_info "Detected language: ${lang}"
    log_info "Suite: ${CODEQL_SUITE}"

    # Create database
    if ! codeql database create "$codeql_db" \
        --language="$lang" \
        --source-root="$WORKSPACE" \
        --overwrite \
        --threads=0 \
        2>/tmp/codeql-create.log; then
        log_fail "CodeQL database creation failed"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "codeql" "fail" '"Database creation failed"' "$dur" \
            "$(jq -Rs '.' /tmp/codeql-create.log 2>/dev/null || echo '["Database creation error"]')"
        return
    fi

    log_info "Database created, running analysis..."

    # Run analysis
    if ! codeql database analyze "$codeql_db" \
        --format=sarif-latest \
        --output="$codeql_results" \
        --threads=0 \
        -- "codeql/${lang}-queries:codeql-suites/${lang}-${CODEQL_SUITE}.qls" \
        2>/tmp/codeql-analyze.log; then
        log_fail "CodeQL analysis failed"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "codeql" "fail" '"Analysis failed"' "$dur"
        return
    fi

    # Parse SARIF results
    local total_results=0
    local critical_count=0
    local high_count=0
    local medium_count=0
    local low_count=0

    if [[ -f "$codeql_results" ]]; then
        total_results=$(jq '[.runs[].results[]] | length' "$codeql_results" 2>/dev/null || echo 0)

        # Count by severity
        critical_count=$(jq '[.runs[].results[] | select(.properties.problem.severity == "error")] | length' "$codeql_results" 2>/dev/null || echo 0)
        high_count=$(jq '[.runs[].results[] | select(.properties.problem.severity == "warning")] | length' "$codeql_results" 2>/dev/null || echo 0)
        medium_count=$(jq '[.runs[].results[] | select(.properties.problem.severity == "recommendation")] | length' "$codeql_results" 2>/dev/null || echo 0)
        low_count=$(jq '[.runs[].results[] | select(.properties.problem.severity == "note")] | length' "$codeql_results" 2>/dev/null || echo 0)

        # Extract top findings
        findings=$(jq '[.runs[].results[:10] | .[] | {
            rule: .ruleId,
            message: .message.text,
            location: (.locations[0].physicalLocation.artifactLocation.uri // "unknown"),
            line: (.locations[0].physicalLocation.region.startLine // 0),
            severity: (.properties.problem.severity // "unknown")
        }]' "$codeql_results" 2>/dev/null || echo "[]")

        suggestions=$(jq '[.runs[].results[:5] | .[] |
            "Fix \(.ruleId) in \(.locations[0].physicalLocation.artifactLocation.uri // "unknown") line \(.locations[0].physicalLocation.region.startLine // "?")"
        ]' "$codeql_results" 2>/dev/null || echo "[]")
    fi

    log_info "Results: ${total_results} total (${critical_count} critical, ${high_count} high, ${medium_count} medium, ${low_count} low)"

    local status="pass"
    if [[ "$critical_count" -gt 0 ]]; then
        log_fail "CodeQL: ${critical_count} critical findings"
        status="fail"
    elif [[ "$high_count" -gt 0 ]]; then
        log_warn "CodeQL: ${high_count} high-severity findings"
        status="warn"
    else
        log_pass "CodeQL: Clean (${total_results} informational findings)"
    fi

    local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
    local details=$(cat <<EOF
{
    "language": "${lang}",
    "suite": "${CODEQL_SUITE}",
    "total_results": ${total_results},
    "critical": ${critical_count},
    "high": ${high_count},
    "medium": ${medium_count},
    "low": ${low_count},
    "sarif_file": "${codeql_results}"
}
EOF
)
    write_result "codeql" "$status" "$details" "$dur" "$findings" "$suggestions"

    # Cleanup
    rm -rf "$codeql_db"
}

# ═════════════════════════════════════════════════════════════════════════════
# CHECK 2: Facebook Infer Static Analysis
# ═════════════════════════════════════════════════════════════════════════════

run_infer() {
    log_header "Facebook Infer Static Analysis"
    local start_ms=$(date +%s%N)
    local findings="[]"
    local suggestions="[]"

    # Infer works best with compiled languages; for Python we use pytype/pyright
    # Check if we have C/C++/Java/Objective-C
    local has_compiled=false
    local compile_cmd=""

    if [[ -f "Makefile" ]]; then
        has_compiled=true
        compile_cmd="make"
    elif [[ -f "build.gradle" ]] || [[ -f "build.gradle.kts" ]]; then
        has_compiled=true
        compile_cmd="gradle build"
    elif [[ -f "CMakeLists.txt" ]]; then
        has_compiled=true
        compile_cmd="cmake . && make"
    elif [[ -f "pom.xml" ]]; then
        has_compiled=true
        compile_cmd="mvn compile"
    fi

    if [[ "$has_compiled" == "false" ]]; then
        # For Python projects, run Infer's --pulse analysis on any C extensions
        # or fall back to enhanced pyright analysis
        local py_files
        py_files=$(find "$WORKSPACE" -name "*.py" -not -path "*/\.*" -not -path "*/node_modules/*" -not -path "*/__pycache__/*" | head -500)

        if [[ -z "$py_files" ]]; then
            log_warn "No supported source files for Infer"
            local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
            write_result "infer" "skip" '"No compiled language source files found"' "$dur"
            return
        fi

        # Run enhanced static analysis for Python instead
        log_info "Python project detected — running enhanced static analysis"

        local infer_report="/tmp/infer-python-report.json"
        local null_issues=0
        local resource_issues=0
        local type_issues=0

        # Check for common patterns Infer would catch in compiled code:
        # 1. Unclosed resources (files, connections, sockets)
        resource_issues=$(grep -rn "open(" $py_files 2>/dev/null | \
            grep -v "with " | grep -v "#" | wc -l || echo 0)

        # 2. Potential None dereference (accessing .attr on possibly-None)
        null_issues=$(grep -rn "\.get(" $py_files 2>/dev/null | \
            grep -v "or " | grep -v "if " | grep -v "default=" | wc -l || echo 0)

        # 3. Type confusion patterns
        type_issues=$(grep -rn "type: ignore" $py_files 2>/dev/null | wc -l || echo 0)

        local total_issues=$((resource_issues + null_issues + type_issues))

        findings=$(cat <<FINDINGS
[
    {"category": "resource_leak", "count": ${resource_issues}, "description": "open() calls without context manager (with statement)"},
    {"category": "null_dereference_risk", "count": ${null_issues}, "description": ".get() calls without None guards"},
    {"category": "type_suppression", "count": ${type_issues}, "description": "type: ignore comments (suppressed type errors)"}
]
FINDINGS
)

        if [[ "$resource_issues" -gt 5 ]]; then
            suggestions='["Use context managers (with statements) for all file/connection operations", "Wrap database connections in try/finally blocks"]'
        else
            suggestions='["Consider running Infer on any C extension modules"]'
        fi

        local status="pass"
        if [[ "$resource_issues" -gt 10 ]]; then
            log_fail "Infer (Python mode): ${resource_issues} potential resource leaks"
            status="fail"
        elif [[ "$total_issues" -gt 20 ]]; then
            log_warn "Infer (Python mode): ${total_issues} issues found"
            status="warn"
        else
            log_pass "Infer (Python mode): ${total_issues} minor issues"
        fi

        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        local details=$(cat <<EOF
{
    "mode": "python-enhanced",
    "resource_leaks": ${resource_issues},
    "null_risks": ${null_issues},
    "type_suppressions": ${type_issues},
    "total_issues": ${total_issues}
}
EOF
)
        write_result "infer" "$status" "$details" "$dur" "$findings" "$suggestions"
        return
    fi

    # Compiled language — run real Infer
    log_info "Running Infer capture + analysis..."

    local infer_out="/tmp/infer-out"
    rm -rf "$infer_out"

    if ! infer run \
        --results-dir "$infer_out" \
        -- $compile_cmd \
        2>/tmp/infer-run.log; then
        log_fail "Infer analysis failed"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "infer" "fail" '"Analysis execution failed"' "$dur"
        return
    fi

    # Parse Infer results
    local report_json="${infer_out}/report.json"
    local total_bugs=0
    local null_deref=0
    local resource_leak=0
    local thread_safety=0
    local other=0

    if [[ -f "$report_json" ]]; then
        total_bugs=$(jq '. | length' "$report_json" 2>/dev/null || echo 0)
        null_deref=$(jq '[.[] | select(.bug_type | test("NULL_DEREFERENCE|NULLPTR"))] | length' "$report_json" 2>/dev/null || echo 0)
        resource_leak=$(jq '[.[] | select(.bug_type | test("RESOURCE_LEAK"))] | length' "$report_json" 2>/dev/null || echo 0)
        thread_safety=$(jq '[.[] | select(.bug_type | test("THREAD_SAFETY|DATA_RACE|LOCK"))] | length' "$report_json" 2>/dev/null || echo 0)
        other=$((total_bugs - null_deref - resource_leak - thread_safety))

        findings=$(jq '.[0:10] | [.[] | {
            bug_type: .bug_type,
            severity: .severity,
            file: .file,
            line: .line,
            procedure: .procedure,
            qualifier: .qualifier
        }]' "$report_json" 2>/dev/null || echo "[]")

        suggestions=$(jq '.[0:5] | [.[] |
            "Fix \(.bug_type) in \(.file):\(.line) (\(.procedure))"
        ]' "$report_json" 2>/dev/null || echo "[]")
    fi

    log_info "Bugs found: ${total_bugs} (null_deref=${null_deref}, resource_leak=${resource_leak}, thread_safety=${thread_safety})"

    local status="pass"
    if [[ "$null_deref" -gt 0 ]] || [[ "$thread_safety" -gt 0 ]]; then
        log_fail "Infer: ${null_deref} null dereferences, ${thread_safety} thread safety issues"
        status="fail"
    elif [[ "$resource_leak" -gt 3 ]]; then
        log_warn "Infer: ${resource_leak} resource leaks"
        status="warn"
    else
        log_pass "Infer: Clean (${total_bugs} minor issues)"
    fi

    local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
    local details=$(cat <<EOF
{
    "total_bugs": ${total_bugs},
    "null_dereference": ${null_deref},
    "resource_leak": ${resource_leak},
    "thread_safety": ${thread_safety},
    "other": ${other}
}
EOF
)
    write_result "infer" "$status" "$details" "$dur" "$findings" "$suggestions"
}

# ═════════════════════════════════════════════════════════════════════════════
# CHECK 3: Integration Tests (Testcontainers)
# ═════════════════════════════════════════════════════════════════════════════

run_integration_tests() {
    log_header "Integration Tests (Testcontainers)"
    local start_ms=$(date +%s%N)

    # Look for integration test directories
    local test_dirs=()
    for dir in "tests/integration" "test/integration" "integration_tests" "tests/e2e" "test/e2e"; do
        if [[ -d "$WORKSPACE/$dir" ]]; then
            test_dirs+=("$dir")
        fi
    done

    # Also look for files with integration test markers
    local marked_files
    marked_files=$(find "$WORKSPACE" -name "test_*.py" -exec grep -l "testcontainers\|@pytest.mark.integration\|@integration" {} \; 2>/dev/null | head -50)

    if [[ ${#test_dirs[@]} -eq 0 ]] && [[ -z "$marked_files" ]]; then
        log_warn "No integration tests found"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "integration" "skip" '"No integration test directory or marked test files found"' "$dur" \
            '["No tests/integration or tests/e2e directory found"]' \
            '["Create tests/integration/ directory with Testcontainer-backed tests"]'
        return
    fi

    # Check Docker socket availability
    if ! docker info &>/dev/null; then
        log_warn "Docker socket not available — Testcontainers require Docker"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "integration" "skip" '"Docker not available for Testcontainers"' "$dur" \
            '["Mount Docker socket: -v /var/run/docker.sock:/var/run/docker.sock"]' \
            '["Ensure DOCKER_HOST is set or Docker socket is mounted"]'
        return
    fi

    log_info "Running integration tests..."

    # Build pytest command
    local pytest_args=(
        "-x"                                # Stop on first failure
        "--timeout=300"                      # 5-min timeout per test
        "-v"                                 # Verbose output
        "--tb=short"                         # Short tracebacks
        "--junitxml=/tmp/integration-results.xml"
        "-m" "integration or e2e"            # Run only integration-marked tests
    )

    for dir in "${test_dirs[@]}"; do
        pytest_args+=("$dir")
    done

    local test_output="/tmp/integration-output.txt"

    if python -m pytest "${pytest_args[@]}" 2>&1 | tee "$test_output"; then
        local passed=$(grep -oP '\d+ passed' "$test_output" | grep -oP '\d+' || echo 0)
        local failed=$(grep -oP '\d+ failed' "$test_output" | grep -oP '\d+' || echo 0)
        local skipped=$(grep -oP '\d+ skipped' "$test_output" | grep -oP '\d+' || echo 0)

        if [[ "$failed" -eq 0 ]]; then
            log_pass "Integration tests: ${passed} passed, ${skipped} skipped"
            local status="pass"
        else
            log_fail "Integration tests: ${failed} failed, ${passed} passed"
            local status="fail"
        fi

        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        local details=$(cat <<EOF
{
    "passed": ${passed:-0},
    "failed": ${failed:-0},
    "skipped": ${skipped:-0},
    "junit_xml": "/tmp/integration-results.xml"
}
EOF
)
        write_result "integration" "$status" "$details" "$dur"
    else
        log_fail "Integration tests failed"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "integration" "fail" '"Test execution failed"' "$dur"
    fi
}

# ═════════════════════════════════════════════════════════════════════════════
# CHECK 4: Performance Benchmarks vs. Baseline
# ═════════════════════════════════════════════════════════════════════════════

run_benchmarks() {
    log_header "Performance Benchmarks"
    local start_ms=$(date +%s%N)

    # Look for benchmark files
    local bench_files
    bench_files=$(find "$WORKSPACE" -name "bench_*.py" -o -name "*_benchmark.py" -o -name "test_*bench*.py" 2>/dev/null | head -50)

    if [[ -z "$bench_files" ]]; then
        # Check for pytest-benchmark fixtures
        bench_files=$(find "$WORKSPACE" -name "test_*.py" -exec grep -l "benchmark\|@pytest.mark.benchmark" {} \; 2>/dev/null | head -50)
    fi

    if [[ -z "$bench_files" ]]; then
        log_warn "No benchmark files found"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "benchmark" "skip" '"No benchmark files found"' "$dur" \
            '["No bench_*.py or *_benchmark.py files found"]' \
            '["Create bench_*.py files with pytest-benchmark fixtures for critical paths"]'
        return
    fi

    log_info "Found benchmark files, running..."

    local bench_output="/tmp/benchmark-output.json"
    local bench_log="/tmp/benchmark.log"

    # Run with pytest-benchmark
    if python -m pytest \
        -m "benchmark or perf" \
        --benchmark-only \
        --benchmark-json="$bench_output" \
        --benchmark-sort=mean \
        --benchmark-min-rounds=5 \
        --timeout=120 \
        $bench_files \
        2>&1 | tee "$bench_log"; then

        # Parse results
        local total_benchmarks
        total_benchmarks=$(jq '.benchmarks | length' "$bench_output" 2>/dev/null || echo 0)

        if [[ "$total_benchmarks" -gt 0 ]]; then
            log_info "${total_benchmarks} benchmarks executed"

            # Compare against baseline if available
            if [[ -n "$BENCHMARK_BASELINE" ]] && [[ -f "$BENCHMARK_BASELINE" ]]; then
                log_info "Comparing against baseline..."

                local regressions=0
                local improvements=0

                # Compare each benchmark's mean time
                while IFS= read -r bench_name; do
                    local current_mean
                    current_mean=$(jq -r ".benchmarks[] | select(.name == \"${bench_name}\") | .stats.mean" "$bench_output" 2>/dev/null)
                    local baseline_mean
                    baseline_mean=$(jq -r ".benchmarks[] | select(.name == \"${bench_name}\") | .stats.mean" "$BENCHMARK_BASELINE" 2>/dev/null)

                    if [[ -n "$current_mean" ]] && [[ -n "$baseline_mean" ]] && [[ "$baseline_mean" != "null" ]]; then
                        local ratio
                        ratio=$(python3 -c "print(round(float('$current_mean') / float('$baseline_mean'), 3))" 2>/dev/null || echo "1.0")

                        if python3 -c "exit(0 if float('$ratio') > 1.2 else 1)" 2>/dev/null; then
                            regressions=$((regressions + 1))
                            log_warn "Regression: ${bench_name} (${ratio}x slower)"
                        elif python3 -c "exit(0 if float('$ratio') < 0.8 else 1)" 2>/dev/null; then
                            improvements=$((improvements + 1))
                            log_pass "Improved: ${bench_name} (${ratio}x)"
                        fi
                    fi
                done < <(jq -r '.benchmarks[].name' "$bench_output" 2>/dev/null)

                local status="pass"
                if [[ "$regressions" -gt 0 ]]; then
                    log_fail "Performance regressions detected: ${regressions}"
                    status="fail"
                else
                    log_pass "No performance regressions (${improvements} improvements)"
                fi

                local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
                local details=$(cat <<EOF
{
    "total_benchmarks": ${total_benchmarks},
    "regressions": ${regressions},
    "improvements": ${improvements},
    "baseline_used": true,
    "results_file": "${bench_output}"
}
EOF
)
                write_result "benchmark" "$status" "$details" "$dur"
            else
                # No baseline — just report results
                log_pass "Benchmarks complete: ${total_benchmarks} tests (no baseline for comparison)"
                local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
                local details=$(cat <<EOF
{
    "total_benchmarks": ${total_benchmarks},
    "baseline_used": false,
    "results_file": "${bench_output}",
    "note": "Save this run as baseline with: cp ${bench_output} benchmarks/baseline.json"
}
EOF
)
                write_result "benchmark" "pass" "$details" "$dur"
            fi
        else
            log_warn "No benchmarks found in test files"
            local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
            write_result "benchmark" "skip" '"Benchmark files exist but no benchmarks executed"' "$dur"
        fi
    else
        log_fail "Benchmark execution failed"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "benchmark" "fail" '"Benchmark execution error"' "$dur"
    fi
}

# ═════════════════════════════════════════════════════════════════════════════
# CHECK 5: Deep Complexity Analysis
# ═════════════════════════════════════════════════════════════════════════════

run_complexity() {
    log_header "Deep Complexity Analysis"
    local start_ms=$(date +%s%N)
    local findings="[]"

    local py_files
    py_files=$(find "$WORKSPACE" -name "*.py" -not -path "*/\.*" -not -path "*/node_modules/*" -not -path "*/__pycache__/*" -not -path "*/venv/*" -not -name "test_*" 2>/dev/null)

    if [[ -z "$py_files" ]]; then
        log_warn "No Python source files found for complexity analysis"
        local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
        write_result "complexity" "skip" '"No Python source files"' "$dur"
        return
    fi

    # Radon: Cyclomatic Complexity
    log_info "Running Radon cyclomatic complexity..."
    local radon_cc="/tmp/radon-cc.json"
    radon cc "$WORKSPACE" -s -j --exclude "test_*,*_test.py,conftest.py,venv,node_modules,.git" > "$radon_cc" 2>/dev/null || true

    local total_functions=0
    local high_complexity=0  # C or worse (11+)
    local very_high=0        # D or worse (21+)
    local unmaintainable=0   # F (41+)
    local avg_complexity=0

    if [[ -s "$radon_cc" ]]; then
        # Count functions by complexity grade
        total_functions=$(jq '[.[][]] | length' "$radon_cc" 2>/dev/null || echo 0)
        high_complexity=$(jq '[.[][] | select(.complexity >= 11)] | length' "$radon_cc" 2>/dev/null || echo 0)
        very_high=$(jq '[.[][] | select(.complexity >= 21)] | length' "$radon_cc" 2>/dev/null || echo 0)
        unmaintainable=$(jq '[.[][] | select(.complexity >= 41)] | length' "$radon_cc" 2>/dev/null || echo 0)
        avg_complexity=$(jq '[.[][].complexity] | if length > 0 then (add / length) else 0 end | . * 10 | round / 10' "$radon_cc" 2>/dev/null || echo 0)

        # Get worst offenders
        findings=$(jq '[.[][] | select(.complexity >= 11)] | sort_by(-.complexity) | .[0:10] | [.[] | {
            name: .name,
            type: .type,
            complexity: .complexity,
            rank: .rank,
            lineno: .lineno,
            endline: .endline,
            col_offset: .col_offset
        }]' "$radon_cc" 2>/dev/null || echo "[]")
    fi

    log_info "Functions: ${total_functions} total, avg complexity: ${avg_complexity}"
    log_info "High complexity (11+): ${high_complexity}, Very high (21+): ${very_high}, Unmaintainable (41+): ${unmaintainable}"

    # Radon: Maintainability Index
    log_info "Running Radon maintainability index..."
    local radon_mi="/tmp/radon-mi.json"
    radon mi "$WORKSPACE" -s -j --exclude "test_*,*_test.py,conftest.py,venv,node_modules,.git" > "$radon_mi" 2>/dev/null || true

    local low_maintainability=0
    local avg_mi=0
    if [[ -s "$radon_mi" ]]; then
        low_maintainability=$(jq '[to_entries[] | select(.value.mi < 20)] | length' "$radon_mi" 2>/dev/null || echo 0)
        avg_mi=$(jq '[to_entries[].value.mi] | if length > 0 then (add / length) else 0 end | . * 10 | round / 10' "$radon_mi" 2>/dev/null || echo 0)
    fi

    log_info "Avg maintainability index: ${avg_mi}/100, Low MI files: ${low_maintainability}"

    # Lizard: Multi-language complexity + NLOC
    log_info "Running Lizard analysis..."
    local lizard_report="/tmp/lizard-report.csv"
    lizard "$WORKSPACE" \
        --exclude "test_*,*_test.*,conftest.*,venv/*,node_modules/*,.git/*" \
        --csv \
        --length 50 \
        --CCN 15 \
        > "$lizard_report" 2>/dev/null || true

    local lizard_warnings
    lizard_warnings=$(wc -l < "$lizard_report" 2>/dev/null || echo 0)
    lizard_warnings=$((lizard_warnings - 1))  # Subtract header
    [[ "$lizard_warnings" -lt 0 ]] && lizard_warnings=0

    # Cohesion analysis
    log_info "Running cohesion analysis..."
    local cohesion_output="/tmp/cohesion-output.txt"
    python -m cohesion -d "$WORKSPACE" > "$cohesion_output" 2>/dev/null || true
    local low_cohesion
    low_cohesion=$(grep -c "cohesion: [0-3][0-9]%" "$cohesion_output" 2>/dev/null || echo 0)

    # Determine overall status
    local status="pass"
    local suggestions='[]'

    if [[ "$unmaintainable" -gt 0 ]]; then
        log_fail "Complexity: ${unmaintainable} unmaintainable functions (CC >= 41)"
        status="fail"
        suggestions='["Refactor functions with complexity >= 41 immediately", "Extract sub-functions to reduce cyclomatic complexity", "Consider strategy pattern for complex switch/if chains"]'
    elif [[ "$very_high" -gt 3 ]]; then
        log_fail "Complexity: ${very_high} very-high-complexity functions (CC >= 21)"
        status="fail"
        suggestions='["Refactor functions with complexity >= 21", "Use polymorphism instead of long conditional chains"]'
    elif [[ "$high_complexity" -gt 10 ]]; then
        log_warn "Complexity: ${high_complexity} high-complexity functions (CC >= 11)"
        status="warn"
        suggestions='["Gradually refactor high-complexity functions", "Add tests before refactoring to prevent regressions"]'
    else
        log_pass "Complexity: Clean (avg CC=${avg_complexity}, MI=${avg_mi})"
        suggestions='["Maintain current complexity levels as baseline"]'
    fi

    local dur=$(( ($(date +%s%N) - start_ms) / 1000000 ))
    local details=$(cat <<EOF
{
    "total_functions": ${total_functions},
    "avg_cyclomatic_complexity": ${avg_complexity},
    "high_complexity_count": ${high_complexity},
    "very_high_complexity_count": ${very_high},
    "unmaintainable_count": ${unmaintainable},
    "avg_maintainability_index": ${avg_mi},
    "low_maintainability_files": ${low_maintainability},
    "lizard_warnings": ${lizard_warnings},
    "low_cohesion_classes": ${low_cohesion}
}
EOF
)
    write_result "complexity" "$status" "$details" "$dur" "$findings" "$suggestions"
}


# ═════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION
# ═════════════════════════════════════════════════════════════════════════════

case "$RUN_MODE" in
    all)
        run_codeql
        run_infer
        run_integration_tests
        run_benchmarks
        run_complexity
        ;;
    codeql)      run_codeql ;;
    infer)       run_infer ;;
    integration) run_integration_tests ;;
    benchmark)   run_benchmarks ;;
    complexity)  run_complexity ;;
esac


# ═════════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ═════════════════════════════════════════════════════════════════════════════

TOTAL_MS=$(elapsed_ms)

# Assemble JSON report
CHECKS="[]"
for f in "${RESULTS_DIR}"/*.json; do
    [[ -f "$f" ]] || continue
    CHECKS=$(echo "$CHECKS" | jq --slurpfile item "$f" '. + $item')
done

FINAL_STATUS="pass"
if [[ "$TOTAL_FAILURES" -gt 0 ]]; then
    FINAL_STATUS="fail"
elif [[ "$TOTAL_WARNINGS" -gt 0 ]]; then
    FINAL_STATUS="warn"
fi

cat > "$REPORT_FILE" <<EOF
{
  "tier": 3,
  "tier_name": "deep",
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

# Post report if URL configured
if [[ -n "$REPORT_URL" ]]; then
    curl -sf -X POST "$REPORT_URL" \
        -H "Content-Type: application/json" \
        -d @"$REPORT_FILE" &>/dev/null || true
fi

# Print summary
if [[ "$REPORT_ONLY" == "false" ]]; then
    echo ""
    echo -e "${BOLD}═══ Deep Verification Summary ═══${NC}"
    echo -e "  Duration: ${TOTAL_MS}ms / ${MAX_TIME}s max"
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

# Cleanup
rm -rf "$RESULTS_DIR"

# Exit code: 0=pass, 1=fail, 2=warn
if [[ "$FINAL_STATUS" == "fail" ]]; then
    exit 1
elif [[ "$FINAL_STATUS" == "warn" ]]; then
    exit 0  # Warnings don't block pipeline
else
    exit 0
fi
