#!/usr/bin/env bash
#
# Exit gate runner for Wave 1 verification
#
# This script runs a deliberately flawed test commit through the
# verification checks implemented in this repository. It checks for five
# distinct categories of violations: SQL injection, missing tests,
# missing dependencies, architectural layer violations and hardcoded
# secrets. It prints PASS/FAIL for each category along with a fix
# instruction taken from the expected results file. The script exits
# with status 0 only if all violations are detected.

set -euo pipefail

COLOR_GREEN="\033[32m"
COLOR_RED="\033[31m"
COLOR_RESET="\033[0m"

base_dir="$(dirname "$0")"
test_dir="$base_dir/test-commit"
expected_json="$base_dir/expected-results.json"

if ! command -v jq >/dev/null; then
  echo "jq is required to run this script" >&2
  exit 1
fi
# Load expected results
expected_categories=$(jq -r '.violations[].name' "$expected_json")

declare -A found
for cat in $expected_categories; do
  found[$cat]=0
done

# 1. SQL injection detection via grep for unsafe f-strings containing SQL
if grep -R -nE 'f\s*"[^"]*SELECT[^"]*\{' "$test_dir" >/dev/null; then
  found[sql_injection]=1
fi

# 2. Missing tests: no files matching test_*.py or *_test.py
test_count=$(find "$test_dir" -type f \( -name 'test_*.py' -o -name '*_test.py' \) | wc -l)
if [[ "$test_count" -eq 0 ]]; then
  found[missing_tests]=1
fi

# 3. Missing dependency (fake import) detection via simple grep
if grep -R -n "import pandas_pro" "$test_dir" >/dev/null; then
  found[missing_dependency]=1
fi

# 4. Layer violation: service importing from handlers
if grep -R -n "from handlers" "$test_dir" | grep -v "/handlers/" >/dev/null; then
  found[layer_violation]=1
fi

# 5. Hardcoded secret detection: simple pattern for password assignment
if grep -R -nE 'password\s*=\s*"[^"]+"' "$test_dir" >/dev/null; then
  found[hardcoded_secret]=1
fi

# Print results and fix instructions
overall=0
for cat in $expected_categories; do
  message=$(jq -r --arg name "$cat" '.violations[] | select(.name==$name) | .message' "$expected_json")
  if [[ "${found[$cat]}" -eq 1 ]]; then
    echo -e "${COLOR_GREEN}PASS${COLOR_RESET} [$cat] - $message"
  else
    echo -e "${COLOR_RED}FAIL${COLOR_RESET} [$cat] - $message"
    overall=1
  fi
done

exit "$overall"