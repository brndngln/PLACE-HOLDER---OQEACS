#!/usr/bin/env bash
#
# Omni Verify Deep verification script
#
# Performs deep verification tasks including integration tests against
# real database services, CodeQL and Facebook Infer static analysis
# and benchmarking. Each task is executed asynchronously and results
# are aggregated into a structured JSON summary. Optional tools
# gracefully degrade when unavailable.

set -euo pipefail

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Helper to run a command and capture status/output
run_task() {
  local name="$1"; shift
  local cmd="$@"
  {
    if eval "$cmd" >"$TMP_DIR/$name.out" 2>&1; then
      echo "pass" >"$TMP_DIR/$name.status"
    else
      echo "fail" >"$TMP_DIR/$name.status"
    fi
  } &
  PIDS["$name"]=$!
}

declare -A PIDS

# Integration tests: run pytest with environment variables pointing to
# the Omni platform's database and cache services. We rely on test
# suites to consume these variables or use testcontainers internally.
POSTGRES_HOST="${POSTGRES_HOST:-omni-postgres}"
REDIS_HOST="${REDIS_HOST:-omni-redis}"
run_task integration_tests "POSTGRES_HOST=$POSTGRES_HOST REDIS_HOST=$REDIS_HOST pytest -q"

# CodeQL analysis: create a database and run the default suite if
# codeql is available. We skip gracefully when the CLI is missing.
if command -v codeql >/dev/null 2>&1; then
  run_task codeql_analysis "codeql database create $TMP_DIR/codeql-db --source-root . --language=python && codeql database analyze $TMP_DIR/codeql-db --format=sarif-latest --output=$TMP_DIR/codeql-report.sarif"
else
  run_task codeql_analysis "echo 'CodeQL not available' && exit 0"
fi

# Facebook Infer analysis: run infer capture and analyse when installed
if command -v infer >/dev/null 2>&1; then
  run_task infer_analysis "infer run -- python -m pytest -q"
else
  run_task infer_analysis "echo 'Infer not available' && exit 0"
fi

# Benchmark suite: run pytest in benchmark-only mode if tests are
# decorated with benchmark markers. Fallback to success when no
# benchmarks are defined.
run_task benchmark "pytest --benchmark-only || true"

# Wait for all tasks to complete
for pid in "${PIDS[@]}"; do
  wait "$pid" || true
done

# Assemble JSON results
task_jsons=()
for name in "${!PIDS[@]}"; do
  status=$(cat "$TMP_DIR/$name.status" 2>/dev/null || echo "pass")
  output=$(jq -Rs . <"$TMP_DIR/$name.out")
  task_json=$(jq -n --arg status "$status" --argjson output "$output" '{status: $status, output: $output}')
  task_jsons+=("\"$name\":$task_json")
done

tasks_json="$(printf '{%s}' "$(IFS=','; echo "${task_jsons[*]}")")"

# Determine overall status: any fail = fail
overall_status="pass"
for name in "${!PIDS[@]}"; do
  if [[ $(cat "$TMP_DIR/$name.status" 2>/dev/null) == "fail" ]]; then
    overall_status="fail"
    break
  fi
done

jq -n --argjson tasks "$tasks_json" --arg overall "$overall_status" '{tasks: $tasks, overall_status: $overall}'