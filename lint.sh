#!/usr/bin/env bash
#
# IaC Security Linting Script
#
# This script runs a suite of linters to enforce security best practices
# across infrastructure as code (IaC) artifacts and shell scripts. It runs
# Hadolint on Dockerfiles, Checkov on Terraform/CloudFormation, and
# ShellCheck on Bash scripts. Warnings from Hadolint do not block the
# pipeline, but missing `set -euo pipefail` directives in shell scripts
# cause an error. The script exits non‑zero if any critical issues are
# detected.

set -euo pipefail
IFS=$'\n\t'

###############################################################################
# Logging helpers
###############################################################################

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
  echo -e "${RED}[ERROR]${NC} $1" >&2
}

###############################################################################
# Find files
###############################################################################

# Root directory to scan; default current directory
ROOT_DIR="${IAC_PATH:-.}"

find_dockerfiles() {
  find "$ROOT_DIR" -maxdepth 4 -type f \( -name '*Dockerfile' -o -name 'Dockerfile.*' \)
}

find_shell_scripts() {
  find "$ROOT_DIR" -maxdepth 4 -type f \( -name '*.sh' -o -perm -u+x \)
}

find_iac_files() {
  find "$ROOT_DIR" -maxdepth 4 -type f \( -name '*.tf' -o -name '*.tf.json' -o -name '*.yaml' -o -name '*.yml' -o -name '*.json' \)
}

###############################################################################
# Lint Dockerfiles with Hadolint
###############################################################################

lint_dockerfiles() {
  local status=0
  info "Running Hadolint on Dockerfiles"
  local files=($(find_dockerfiles))
  if [ ${#files[@]} -eq 0 ]; then
    info "No Dockerfiles found"
    return 0
  fi
  for file in "${files[@]}"; do
    if ! hadolint "$file"; then
      warn "Hadolint found issues in $file"
      # Do not set failure for hadolint; warnings only
    fi
  done
  return $status
}

###############################################################################
# Lint IaC with Checkov
###############################################################################

lint_iac() {
  local dir="$ROOT_DIR"
  info "Running Checkov on IaC files"
  if ! checkov -q -d "$dir"; then
    error "Checkov detected IaC misconfigurations"
    return 1
  fi
  return 0
}

###############################################################################
# Lint Shell scripts with ShellCheck and enforce set -euo pipefail
###############################################################################

lint_shell() {
  local status=0
  info "Running ShellCheck on scripts"
  local files=($(find_shell_scripts))
  if [ ${#files[@]} -eq 0 ]; then
    info "No shell scripts found"
    return 0
  fi
  for file in "${files[@]}"; do
    if ! shellcheck -e SC1091 "$file"; then
      error "ShellCheck failed on $file"
      status=1
    fi
    # Enforce 'set -euo pipefail' after shebang if present
    if head -n 2 "$file" | grep -qE '^#!/'; then
      if ! head -n 3 "$file" | grep -q 'set -euo pipefail'; then
        error "Missing 'set -euo pipefail' in $file"
        status=1
      fi
    fi
  done
  return $status
}

###############################################################################
# Main
###############################################################################

failures=0
lint_dockerfiles || true
if ! lint_iac; then
  failures=$((failures+1))
fi
if ! lint_shell; then
  failures=$((failures+1))
fi

if [ "$failures" -ne 0 ]; then
  error "IaC security linting failed"
  exit 1
else
  info "IaC security linting completed successfully"
  exit 0
fi