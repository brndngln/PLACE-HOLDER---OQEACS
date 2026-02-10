#!/usr/bin/env bash
set -euo pipefail

echo "=== Omni Quantum Container Status ==="
docker ps -a --filter "label=omni.quantum.component" \
  --format 'table {{.Names}}\t{{.Status}}\t{{.RunningFor}}\t{{.Label "omni.quantum.tier"}}\t{{.Label "omni.quantum.critical"}}'

echo
for tier in critical high standard; do
  echo "=== ${tier^^} TIER ==="
  docker ps -a --filter "label=omni.quantum.tier=${tier}" \
    --format '  {{.Names}} | {{.Status}}' || true
  echo
done

echo "=== Unhealthy Containers ==="
UNHEALTHY=$(docker ps --filter "label=omni.quantum.component" --filter "health=unhealthy" --format '{{.Names}}')
if [[ -z "$UNHEALTHY" ]]; then
  echo "  none"
else
  echo "$UNHEALTHY" | sed 's/^/  /'
fi

echo
echo "=== Stopped Containers ==="
STOPPED=$(docker ps -a --filter "label=omni.quantum.component" --filter "status=exited" --format '{{.Names}}')
if [[ -z "$STOPPED" ]]; then
  echo "  none"
else
  echo "$STOPPED" | sed 's/^/  /'
fi

echo
echo "=== Resource Usage (running only) ==="
RUNNING=$(docker ps --filter "label=omni.quantum.component" --format '{{.Names}}')
if [[ -z "$RUNNING" ]]; then
  echo "  no running omni containers"
else
  docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}' $RUNNING
fi
