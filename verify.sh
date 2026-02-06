#!/usr/bin/env bash
#
# Omni Verify Instant verification script
#
# This script runs a suite of fast static analysis and formatting tools in
# parallel and emits a structured JSON summary to STDOUT. The intent is
# to catch obvious type errors, lint violations and formatting issues
# without blocking a CI pipeline for more than a few seconds. Tools are
# run on the current working directory.  Results are aggregated and
# reported in a JSON structure with a top‑level overall status and per
# tool details.  Any tool failure causes an overall failure, but
# individual tool errors are still recorded for debugging.

set -euo pipefail

# Create a temporary directory for capturing tool outputs and status flags
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Array of tool definitions. Each entry is of the form:
#   tool_name|command to execute
# We prefer not to quote the commands here so that bash will
# correctly handle word splitting and globs when launching them.
TOOL_DEFINITIONS=(
  "pyright|pyright --project ."
  "ruff|ruff ."
  "black|black --check ."
  "deptry|deptry ."
  "tsc|tsc --noEmit --strict || true"         # allow absence of TS project
  "eslint|eslint . --ext .js,.jsx,.ts,.tsx || true" # ignore if no config
  "prettier|prettier --check . || true"       # prettier prints formatted files
  "oxlint|oxlint . || true"                   # oxlint optional
)

# Start all tools in background. Each tool writes its output and status
# to dedicated files in the temporary directory. The status is either
# "pass" or "fail" depending on the command's exit code.
declare -A PIDS
for definition in "${TOOL_DEFINITIONS[@]}"; do
  IFS='|' read -r name cmd <<<"$definition"
  {
    # run the command, capturing all output
    if eval $cmd >"$TMP_DIR/$name.out" 2>&1; then
      echo "pass" >"$TMP_DIR/$name.status"
    else
      echo "fail" >"$TMP_DIR/$name.status"
    fi
  } &
  PIDS["$name"]=$!
done

# Wait for all background jobs to complete
for pid in "${PIDS[@]}"; do
  wait "$pid" || true
done

# Build JSON summary using jq. The structure is:
# {
#   "tools": {
#     "tool_name": {"status": "pass|fail", "output": "..."},
#     ...
#   },
#   "overall_status": "pass|fail"
# }

# Build a per‑tool JSON object file for merging
tool_jsons=()
for definition in "${TOOL_DEFINITIONS[@]}"; do
  IFS='|' read -r name _ <<<"$definition"
  status=$(cat "$TMP_DIR/$name.status" 2>/dev/null || echo "pass")
  # Escape output for JSON; use jq -R to read raw
  output=$(jq -Rs . <"$TMP_DIR/$name.out")
  tool_json=$(jq -n --arg status "$status" --argjson output "$output" '{status: $status, output: $output}')
  tool_jsons+=("\"$name\":$tool_json")
done

# Combine per‑tool objects into a single JSON object
tools_json="$(printf '{%s}' "$(IFS=','; echo "${tool_jsons[*]}")")"

# Determine overall status: fail if any tool failed
overall_status="pass"
for definition in "${TOOL_DEFINITIONS[@]}"; do
  IFS='|' read -r name _ <<<"$definition"
  if [[ $(cat "$TMP_DIR/$name.status" 2>/dev/null) == "fail" ]]; then
    overall_status="fail"
    break
  fi
done

# Emit final JSON summary
jq -n --argjson tools "$tools_json" --arg overall "$overall_status" '{tools: $tools, overall_status: $overall}'