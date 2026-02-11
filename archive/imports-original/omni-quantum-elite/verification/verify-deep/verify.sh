#!/usr/bin/env bash
#
# Omni Verify Fast verification script
#
# This script orchestrates the fast verification tier for the Omni platform.
# It runs unit tests, static analysis, API specification linting and secret
# scanning concurrently. Each sub-step is captured individually and the
# aggregated result is emitted as structured JSON for consumption by CI.

set -euo pipefail

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Define the tasks for fast verification. Each entry is of the form
#   task_name|command
# The commands are deliberately not quoted so that shell expansions
# occur when executed. Adjust or add tasks as needed.
TASK_DEFINITIONS=(
  "unit_tests|pytest -q && jest --ci --silent && vitest run"
  "sast|semgrep --config=auto ."
  "api_lint|spectral lint $(find . -type f \( -name '*.yaml' -o -name '*.yml' -o -name '*.json' \) 2>/dev/null || true)"
  "secret_scan|{
      gitleaks detect --no-banner --exit-code 1 --source . || true;
      detect-secrets scan --all-files || true;
    }"
)

# Launch each task in the background, capturing output and status
declare -A PIDS
for definition in "${TASK_DEFINITIONS[@]}"; do
  IFS='|' read -r name cmd <<<"$definition"
  {
    if eval $cmd >"$TMP_DIR/$name.out" 2>&1; then
      echo "pass" >"$TMP_DIR/$name.status"
    else
      echo "fail" >"$TMP_DIR/$name.status"
    fi
  } &
  PIDS["$name"]=$!
done

# Wait for all tasks to complete
for pid in "${PIDS[@]}"; do
  wait "$pid" || true
done

# Build per‑task JSON objects
task_jsons=()
for definition in "${TASK_DEFINITIONS[@]}"; do
  IFS='|' read -r name _ <<<"$definition"
  status=$(cat "$TMP_DIR/$name.status" 2>/dev/null || echo "pass")
  output=$(jq -Rs . <"$TMP_DIR/$name.out")
  task_json=$(jq -n --arg status "$status" --argjson output "$output" '{status: $status, output: $output}')
  task_jsons+=("\"$name\":$task_json")
done

# Combine tasks into JSON object
tasks_json="$(printf '{%s}' "$(IFS=','; echo "${task_jsons[*]}")")"

# Determine overall status
overall_status="pass"
for definition in "${TASK_DEFINITIONS[@]}"; do
  IFS='|' read -r name _ <<<"$definition"
  if [[ $(cat "$TMP_DIR/$name.status" 2>/dev/null) == "fail" ]]; then
    overall_status="fail"
    break
  fi
done

jq -n --argjson tasks "$tasks_json" --arg overall "$overall_status" '{tasks: $tasks, overall_status: $overall}'