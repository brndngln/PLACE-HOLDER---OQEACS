#!/usr/bin/env bash
set -euo pipefail

# Required env: IMAGE, SERVICE, HEALTH_URL, TRAEFIK_LABEL
IMAGE="${IMAGE:?IMAGE required}"
SERVICE="${SERVICE:?SERVICE required}"
HEALTH_URL="${HEALTH_URL:?HEALTH_URL required}"
TRAEFIK_LABEL="${TRAEFIK_LABEL:?TRAEFIK_LABEL required}"
NETWORK="${NETWORK:-omni-quantum-network}"
MM_WEBHOOK="http://omni-mattermost-webhook:8066"
BASELINE_LATENCY="${BASELINE_LATENCY:-200}"
ERROR_THRESHOLD="${ERROR_THRESHOLD:-5}"
MONITOR_DURATION="${MONITOR_DURATION:-300}"
DRAIN_SECONDS="${DRAIN_SECONDS:-30}"

notify_mm() {
  curl -s -X POST "${MM_WEBHOOK}" -H "Content-Type: application/json" \
    -d "{\"channel\":\"$1\",\"text\":\"$2\"}"
}

rollback() {
  echo "Rolling back: stopping green, restarting blue..."
  docker rm -f "${SERVICE}-green" 2>/dev/null || true
  docker start "${SERVICE}-blue" 2>/dev/null || true
  notify_mm "#incidents" "\u274c Deploy FAILED for ${SERVICE} — rolled back to previous version"
  exit 1
}

echo "=== Blue-Green Deploy: ${SERVICE} ==="
echo "Image: ${IMAGE}"

# Step 1: Pull new image
echo "[1/8] Pulling image..."
docker pull "${IMAGE}"

# Step 2: Start green container
echo "[2/8] Starting green container..."
docker run -d \
  --name "${SERVICE}-green" \
  --network "${NETWORK}" \
  --label "traefik.enable=false" \
  --restart unless-stopped \
  "${IMAGE}"

# Step 3: Health check green (up to 60s)
echo "[3/8] Waiting for green to become healthy..."
GREEN_HEALTHY=false
for i in $(seq 1 12); do
  if curl -sf "${HEALTH_URL}" >/dev/null 2>&1; then
    GREEN_HEALTHY=true
    echo "  Green healthy after $((i * 5))s"
    break
  fi
  sleep 5
done

# Step 4/5: Switch or rollback
if [ "${GREEN_HEALTHY}" = "true" ]; then
  echo "[4/8] Switching traffic to green..."
  # Update Traefik labels on green to receive traffic
  docker container update \
    --label-add "traefik.enable=true" \
    --label-add "traefik.http.routers.${SERVICE}.rule=${TRAEFIK_LABEL}" \
    --label-add "traefik.http.routers.${SERVICE}.tls.certresolver=letsencrypt" \
    "${SERVICE}-green" 2>/dev/null || \
  docker stop "${SERVICE}-green" && \
  docker run -d \
    --name "${SERVICE}-green-live" \
    --network "${NETWORK}" \
    --label "traefik.enable=true" \
    --label "traefik.http.routers.${SERVICE}.rule=${TRAEFIK_LABEL}" \
    --label "traefik.http.routers.${SERVICE}.tls.certresolver=letsencrypt" \
    --restart unless-stopped \
    "${IMAGE}" && \
  docker rm -f "${SERVICE}-green" 2>/dev/null && \
  docker rename "${SERVICE}-green-live" "${SERVICE}-green"

  echo "[5/8] Draining blue (${DRAIN_SECONDS}s)..."
  sleep "${DRAIN_SECONDS}"
  docker stop "${SERVICE}-blue" 2>/dev/null || true
else
  echo "[FAIL] Green never became healthy"
  docker rm -f "${SERVICE}-green" 2>/dev/null || true
  notify_mm "#incidents" "\u274c Deploy FAILED for ${SERVICE}: green container unhealthy after 60s"
  exit 1
fi

# Step 6: Post-deploy validation
echo "[6/8] Post-deploy validation..."
DEPLOY_LATENCY=$(curl -sf -o /dev/null -w '%{time_total}' "${HEALTH_URL}" | awk '{printf "%.0f", $1 * 1000}')
echo "  Health endpoint latency: ${DEPLOY_LATENCY}ms (baseline: ${BASELINE_LATENCY}ms)"
if [ "${DEPLOY_LATENCY}" -gt "$((BASELINE_LATENCY * 3))" ]; then
  echo "  WARNING: Latency ${DEPLOY_LATENCY}ms exceeds 3x baseline"
  notify_mm "#incidents" "\u26a0\ufe0f ${SERVICE} deploy latency ${DEPLOY_LATENCY}ms exceeds 3x baseline (${BASELINE_LATENCY}ms)"
fi

# Step 7: Monitor for error rate (5 min window)
echo "[7/8] Monitoring for ${MONITOR_DURATION}s (error threshold: ${ERROR_THRESHOLD}%)..."
MONITOR_END=$(($(date +%s) + MONITOR_DURATION))
TOTAL_CHECKS=0
FAILED_CHECKS=0

while [ "$(date +%s)" -lt "${MONITOR_END}" ]; do
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
  if ! curl -sf "${HEALTH_URL}" >/dev/null 2>&1; then
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
  fi

  if [ "${TOTAL_CHECKS}" -gt 0 ]; then
    ERROR_RATE=$((FAILED_CHECKS * 100 / TOTAL_CHECKS))
    if [ "${ERROR_RATE}" -gt "${ERROR_THRESHOLD}" ]; then
      echo "  ERROR RATE ${ERROR_RATE}% exceeds threshold — rolling back"
      rollback
    fi
  fi
  sleep 10
done

FINAL_ERROR_RATE=$((FAILED_CHECKS * 100 / TOTAL_CHECKS))
echo "  Monitoring complete: ${FINAL_ERROR_RATE}% error rate (${FAILED_CHECKS}/${TOTAL_CHECKS} failed)"

if [ "${FINAL_ERROR_RATE}" -gt "${ERROR_THRESHOLD}" ]; then
  rollback
fi

# Step 8: Finalize
echo "[8/8] Finalizing deployment..."
docker rm -f "${SERVICE}-blue" 2>/dev/null || true
docker rename "${SERVICE}-green" "${SERVICE}-blue"

notify_mm "#deployments" "\u2705 Deployed ${SERVICE} — image: ${IMAGE}, error rate: ${FINAL_ERROR_RATE}%"
echo "=== Blue-Green Deploy Complete ==="
