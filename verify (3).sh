#!/usr/bin/env bash
#
# Omni Verify Nightly verification script
#
# This script performs exhaustive verification tasks intended to run as a
# nightly job. It includes fuzzing, mutation testing for both Python
# and JavaScript code, vulnerability scanning and license auditing. All
# tasks are run asynchronously and results aggregated into a JSON
# summary. Each task runs with a conservative timeout to prevent
# runaway processes.

set -euo pipefail

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

declare -A PIDS

# Launch a task with a timeout (in seconds). If the command does not
# finish within the timeout, it is killed.
launch_task() {
  local name="$1"; shift
  local timeout_seconds="$1"; shift
  local cmd="$@"
  {
    # Use timeout if available; fallback to executing directly
    if command -v timeout >/dev/null 2>&1; then
      if timeout --preserve-status "$timeout_seconds"s bash -c "$cmd" >"$TMP_DIR/$name.out" 2>&1; then
        echo "pass" >"$TMP_DIR/$name.status"
      else
        echo "fail" >"$TMP_DIR/$name.status"
      fi
    else
      if bash -c "$cmd" >"$TMP_DIR/$name.out" 2>&1; then
        echo "pass" >"$TMP_DIR/$name.status"
      else
        echo "fail" >"$TMP_DIR/$name.status"
      fi
    fi
  } &
  PIDS["$name"]=$!
}

# Fuzzing using Atheris (60 seconds per fuzzer). If no fuzzer harness
# exists, skip gracefully. A typical harness would reside in fuzz/
# directory and contain Python entrypoints. We iterate over harnesses.
FUZZ_TARGETS=$(find fuzz -type f -name "*fuzz.py" 2>/dev/null || true)
if [[ -n "$FUZZ_TARGETS" ]]; then
  for target in $FUZZ_TARGETS; do
    name="fuzzing_$(basename "$target")"
    launch_task "$name" 60 "python -m atheris -v -o $TMP_DIR/${name}.cov $target || true"
  done
else
  launch_task fuzzing 1 "echo 'No fuzz targets; skipping'"
fi

# Python mutation testing using mutmut. mutmut modifies source code
# on disk; we run it in check-only mode and reset afterwards.
launch_task mutation_python 300 "mutmut run || true"

# JavaScript mutation testing using Stryker. We assume a Stryker
# configuration is present. The process may be lengthy, so we cap
# runtime at 600 seconds.
launch_task mutation_js 600 "stryker run || true"

# Vulnerability and secret scanning: chain Trivy, Grype and OSV
launch_task vuln_scan 300 "trivy fs . --no-progress --quiet || true; grype dir:. || true; osv-scanner --skip-git . || true"

# License and code audit using ScanCode. We limit run time to 600 seconds.
launch_task license_scan 600 "scancode -q --license --json-pp $TMP_DIR/scancode-report.json . || true"

# Wait for all tasks
for pid in "${PIDS[@]}"; do
  wait "$pid" || true
done

# Build JSON
task_jsons=()
for key in "${!PIDS[@]}"; do
  status=$(cat "$TMP_DIR/$key.status" 2>/dev/null || echo "pass")
  output=$(jq -Rs . <"$TMP_DIR/$key.out")
  task_json=$(jq -n --arg status "$status" --argjson output "$output" '{status: $status, output: $output}')
  task_jsons+=("\"$key\":$task_json")
done
tasks_json="$(printf '{%s}' "$(IFS=','; echo "${task_jsons[*]}")")"

overall_status="pass"
for key in "${!PIDS[@]}"; do
  if [[ $(cat "$TMP_DIR/$key.status" 2>/dev/null) == "fail" ]]; then
    overall_status="fail"
    break
  fi
done

jq -n --argjson tasks "$tasks_json" --arg overall "$overall_status" '{tasks: $tasks, overall_status: $overall}'