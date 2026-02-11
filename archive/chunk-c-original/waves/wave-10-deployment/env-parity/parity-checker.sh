#!/bin/bash
# ENVIRONMENT PARITY CHECKER — OMNI QUANTUM ELITE v3.0
set -euo pipefail
echo "Exporting current environment configuration..."
docker ps --format "{{.Names}}\t{{.Image}}" | grep omni- | while read name image; do
    echo "$name: $image"
done
echo "Export complete"
