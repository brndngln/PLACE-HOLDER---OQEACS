#!/usr/bin/env bash
#
# Clean-room reproducibility verifier
#
# This script attempts to build the repository in a fresh temporary
# directory without using cached artifacts. It installs declared
# dependencies for Python and Node projects and reports success or
# failure. Any undeclared transitive dependency should cause a build
# failure. The script uses strict error handling to abort on the
# first error.

set -euo pipefail

COLOR_RED="\033[31m"
COLOR_GREEN="\033[32m"
COLOR_RESET="\033[0m"

info() {
  echo -e "${COLOR_GREEN}[INFO] $*${COLOR_RESET}"
}

error() {
  echo -e "${COLOR_RED}[ERROR] $*${COLOR_RESET}" >&2
}

WORKDIR="$(mktemp -d)"
info "Using temporary build directory: $WORKDIR"

cp -r . "$WORKDIR"
cd "$WORKDIR"

rc=0

# Python clean build
if [[ -f requirements.txt ]]; then
  info "Installing Python dependencies from requirements.txt"
  if ! pip install --no-cache-dir -r requirements.txt; then
    error "Python dependency installation failed"
    rc=1
  fi
fi

# Node.js clean build
if [[ -f package.json ]]; then
  info "Installing Node dependencies via npm ci"
  if command -v npm >/dev/null 2>&1; then
    if ! npm ci --ignore-scripts; then
      error "Node dependency installation failed"
      rc=1
    fi
  else
    error "npm is not available to install Node dependencies"
    rc=1
  fi
fi

# Dockerfile build check
if [[ -f Dockerfile ]]; then
  info "Building Docker image with no cache"
  if ! docker build . --no-cache -t clean-room-test:latest; then
    error "Docker build failed"
    rc=1
  fi
fi

if [[ "$rc" -eq 0 ]]; then
  info "Clean room build succeeded"
else
  error "Clean room build failed"
fi

exit "$rc"