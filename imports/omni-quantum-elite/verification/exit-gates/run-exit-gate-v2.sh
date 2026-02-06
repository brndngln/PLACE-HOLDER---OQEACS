#!/usr/bin/env bash
#
# Exit Gate Test Script for Wave 2
#
# This script verifies that the context intelligence microservices operate
# correctly and within performance constraints. It performs the following
# checks:
#   1. The context compiler returns a curated context with anti‑patterns
#      included and respects a token budget. Response time < 500ms.
#   2. The tool selector returns relevant tools for PostgreSQL and filters out
#      unrelated tools. Response time < 500ms.
#   3. The spec generator produces a detailed specification with at least
#      ten API endpoints, includes data model and authentication sections,
#      and achieves a score ≥ 8.0. Response time < 1.5s.
#   4. Each MCP microservice responds in under 500ms via its health endpoint.
#
# The script reports PASS/FAIL for each check and exits with code 0 only if
# all checks pass. Colored output aids readability.

set -euo pipefail

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

print_pass() {
  echo -e "${GREEN}PASS${NC} — $1"
}

print_fail() {
  echo -e "${RED}FAIL${NC} — $1"
}

fail_count=0

# Read the task description from file and compress whitespace
task=$(tr '\n' ' ' < "$(dirname "$0")/test-task-description.md" | sed 's/  */ /g')

###############################################################################
# Check 1: Context Compiler
###############################################################################

# Invoke the context compiler
ctx_time=$(curl -s -o ctx.json -w '%{time_total}' \
  -H 'Content-Type: application/json' \
  -d "{\"task\":\"$task\"}" \
  http://context-compiler:8325/api/v1/compile)

# Verify response time < 0.5 seconds
ctx_time_ok=$(awk -v t="$ctx_time" 'BEGIN { print (t < 0.5) ? 0 : 1 }')

# Parse JSON using Python for portability
ctx_check=$(python3 - <<'PY' || echo 1
import json, sys
with open('ctx.json') as f:
    data = json.load(f)
context = data.get('context', '')
token_count = int(data.get('token_count', 0))
# Ensure token count <= 2000 and anti patterns included
if token_count <= 2000 and ('SQL injection' in context.lower() or 'sql injection' in context.lower()):
    sys.exit(0)
sys.exit(1)
PY
)

if [ "$ctx_time_ok" -eq 0 ] && [ "$ctx_check" -eq 0 ]; then
  print_pass "context compiler"
else
  print_fail "context compiler"
  fail_count=$((fail_count + 1))
fi

###############################################################################
# Check 2: Tool Selector
###############################################################################

# Invoke the tool selector
tool_time=$(curl -s -o tools.json -w '%{time_total}' \
  -H 'Content-Type: application/json' \
  -d "{\"task\":\"$task\"}" \
  http://tool-selector:8326/api/v1/select)

tool_time_ok=$(awk -v t="$tool_time" 'BEGIN { print (t < 0.5) ? 0 : 1 }')

tool_check=$(python3 - <<'PY' || echo 1
import json, sys, re
with open('tools.json') as f:
    data = json.load(f)
names = [t.get('name', '').lower() for t in data.get('tools', [])]
# Check that at least one tool mentions Postgres and none mention React
has_pg = any('postgres' in n or 'postgresql' in n for n in names)
has_react = any('react' in n for n in names)
if has_pg and not has_react:
    sys.exit(0)
sys.exit(1)
PY
)

if [ "$tool_time_ok" -eq 0 ] && [ "$tool_check" -eq 0 ]; then
  print_pass "tool selector"
else
  print_fail "tool selector"
  fail_count=$((fail_count + 1))
fi

###############################################################################
# Check 3: Spec Generator
###############################################################################

# Invoke the spec generator
spec_time=$(curl -s -o spec.json -w '%{time_total}' \
  -H 'Content-Type: application/json' \
  -d "{\"task\":\"$task\"}" \
  http://spec-generator:8332/api/v1/generate)

spec_time_ok=$(awk -v t="$spec_time" 'BEGIN { print (t < 1.5) ? 0 : 1 }')

spec_check=$(python3 - <<'PY' || echo 1
import json, re, sys
with open('spec.json') as f:
    data = json.load(f)
status = data.get('status')
score = float(data.get('score', 0))
spec = data.get('spec', '')
# Count HTTP verbs as a proxy for endpoint count
endpoint_count = len(re.findall(r'\b(?:GET|POST|PUT|DELETE|PATCH)\b', spec))
# Check conditions: approved, score >= 8, includes Data Model and Authentication, >=10 endpoints
if status == 'approved' and score >= 8 and 'data model' in spec.lower() and 'auth' in spec.lower() and endpoint_count >= 10:
    sys.exit(0)
sys.exit(1)
PY
)

if [ "$spec_time_ok" -eq 0 ] && [ "$spec_check" -eq 0 ]; then
  print_pass "spec generator"
else
  print_fail "spec generator"
  fail_count=$((fail_count + 1))
fi

###############################################################################
# Check 4: MCP Services Health
###############################################################################

check_service() {
  local name="$1"
  local url="$2"
  local time=$(curl -s -o /dev/null -w '%{time_total}' "$url")
  local ok=$(awk -v t="$time" 'BEGIN { print (t < 0.5) ? 0 : 1 }')
  if [ "$ok" -eq 0 ]; then
    print_pass "$name"
  else
    print_fail "$name"
    fail_count=$((fail_count + 1))
  fi
}

check_service "package registry" "http://mcp-package-registry:8327/health"
check_service "docs" "http://mcp-docs:8328/health"
check_service "schema" "http://mcp-schema:8329/health"
check_service "pipeline" "http://mcp-pipeline:8330/health"

###############################################################################
# Final Result
###############################################################################

if [ $fail_count -eq 0 ]; then
  echo -e "${GREEN}All checks passed${NC}"
  exit 0
else
  echo -e "${RED}$fail_count check(s) failed${NC}"
  exit 1
fi