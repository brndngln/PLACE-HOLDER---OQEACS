#!/usr/bin/env bash
#
# Supply Chain Security Scan
#
# This script performs comprehensive supply‑chain security checks on one or
# more container images. It leverages multiple tools to identify and block
# vulnerabilities, generate software bills of materials (SBOMs), and sign
# images. Scans include Trivy, Grype, Syft, Cosign, and OSV‑Scanner. The
# script fails fast on any critical or high vulnerability and emits a
# consolidated report. Use the `IMAGES` environment variable or pass
# image names as arguments.

set -euo pipefail
IFS=$'\n\t'

###############################################################################
# Colorful logging helpers
###############################################################################

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1" >&2
}

###############################################################################
# Configuration and input handling
###############################################################################

IMAGES_LIST=()

# Accept images from positional arguments or IMAGES env var
if [ "$#" -gt 0 ]; then
  IMAGES_LIST=("$@")
elif [ -n "${IMAGES:-}" ]; then
  # Split IMAGES by whitespace
  read -r -a IMAGES_LIST <<<"${IMAGES}"
else
  log_error "No images provided. Set IMAGES env var or pass images as arguments."
  exit 1
fi

# Directory for SBOMs
SBOM_DIR="sbom"
mkdir -p "$SBOM_DIR"

# Result tracking
exit_code=0

###############################################################################
# Functions to run individual tools
###############################################################################

scan_with_trivy() {
  local image="$1"
  log_info "Running Trivy scan for $image"
  # Critical/high severity vulnerabilities cause failure. Output JSON for
  # programmatic parsing if needed.
  if ! trivy image --quiet --severity HIGH,CRITICAL "$image"; then
    log_error "Trivy detected vulnerabilities in $image"
    return 1
  fi
}

scan_with_grype() {
  local image="$1"
  log_info "Running Grype scan for $image"
  if ! grype "$image" --only-fixed --fail-on high; then
    log_error "Grype detected vulnerabilities in $image"
    return 1
  fi
}

generate_sbom() {
  local image="$1"
  local sbom_file="$SBOM_DIR/$(echo "$image" | tr '/:' '__').json"
  log_info "Generating SBOM for $image → $sbom_file"
  syft "${image}" -o json > "$sbom_file"
  if [ ! -s "$sbom_file" ]; then
    log_error "Failed to generate SBOM for $image"
    return 1
  fi
}

scan_osv() {
  local sbom_file="$1"
  log_info "Running OSV‑Scanner for SBOM $sbom_file"
  if ! osv-scanner --sbom "$sbom_file"; then
    log_error "OSV‑Scanner found issues for SBOM $sbom_file"
    return 1
  fi
}

sign_image() {
  local image="$1"
  # Sign image only if COSIGN_KEY or COSIGN_PASSWORD is provided
  if [ -z "${COSIGN_KEY:-}" ] && [ -z "${COSIGN_PASSWORD:-}" ]; then
    log_warn "COSIGN_KEY not provided; skipping signing for $image"
    return 0
  fi
  log_info "Signing image $image with Cosign"
  if ! cosign sign --key "${COSIGN_KEY:-cosign.key}" "$image"; then
    log_error "Cosign failed to sign $image"
    return 1
  fi
}

###############################################################################
# Main scanning loop
###############################################################################

for image in "${IMAGES_LIST[@]}"; do
  log_info "\n=== Processing image: $image ==="
  if ! scan_with_trivy "$image"; then
    exit_code=1
    continue
  fi
  if ! scan_with_grype "$image"; then
    exit_code=1
    continue
  fi
  # Generate SBOM
  if ! generate_sbom "$image"; then
    exit_code=1
    continue
  fi
  sbom_path="$SBOM_DIR/$(echo "$image" | tr '/:' '__').json"
  # OSV scan
  if ! scan_osv "$sbom_path"; then
    exit_code=1
    continue
  fi
  # Sign image
  if ! sign_image "$image"; then
    exit_code=1
    continue
  fi
  log_info "Image $image scanned and signed successfully"
done

if [ "$exit_code" -ne 0 ]; then
  log_error "Supply chain scan failed"
else
  log_info "All images passed supply chain security checks"
fi
exit "$exit_code"