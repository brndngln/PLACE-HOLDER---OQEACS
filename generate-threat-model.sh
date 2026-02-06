#!/usr/bin/env bash
#
# Generate Threat Model
#
# This script uses Threagile to generate a threat model for a specified
# service and stores the resulting model in the Qdrant `threat_models`
# collection. Placeholders in the template configuration are replaced
# dynamically. Requires Python, pip and qdrant-client.

set -euo pipefail
IFS=$'\n\t'

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

log() {
  local level=$1; shift
  local color="$GREEN"
  case "$level" in
    INFO) color="$GREEN";;
    WARN) color="$YELLOW";;
    ERROR) color="$RED";;
  esac
  echo -e "${color}[$level]${NC} $*"
}

# Input service name
if [ $# -lt 1 ]; then
  log ERROR "Usage: $0 <service-name>"
  exit 1
fi
SERVICE_NAME="$1"

# Determine current date
DATE=$(date -I)

TEMPLATE="$(dirname "$0")/threagile-config.yaml"
TMP_MODEL=$(mktemp)

# Replace placeholders in template
sed "s/\${SERVICE_NAME}/$SERVICE_NAME/g; s/\${DATE}/$DATE/g" "$TEMPLATE" > "$TMP_MODEL"

# Ensure Threagile is installed
if ! command -v threagile >/dev/null 2>&1; then
  log INFO "Installing Threagile"
  pip install --no-cache-dir threagile==1.0.0
fi

# Generate threat model; output JSON for programmatic ingestion
OUTPUT_DIR=$(mktemp -d)
log INFO "Generating threat model for service $SERVICE_NAME"
threagile --model "$TMP_MODEL" --output "$OUTPUT_DIR" --output-format json

MODEL_JSON="$OUTPUT_DIR/model.json"
if [ ! -f "$MODEL_JSON" ]; then
  log ERROR "Failed to generate threat model JSON"
  exit 1
fi

# Store in Qdrant
log INFO "Persisting threat model into Qdrant"
# Export environment variables for the inline Python script
export SERVICE_NAME_ENV="$SERVICE_NAME"
export MODEL_JSON="$MODEL_JSON"
export DATE_ENV="$DATE"
python3 - <<'PY'
import json, os, random
from qdrant_client import QdrantClient
from qdrant_client.http import models

service = os.environ.get('SERVICE_NAME_ENV')
model_path = os.environ.get('MODEL_JSON')
date = os.environ.get('DATE_ENV')
qdrant_host = os.getenv('QDRANT_HOST', 'omni-qdrant')
qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
collection = 'threat_models'
client = QdrantClient(host=qdrant_host, port=qdrant_port)

try:
    client.get_collection(collection)
except Exception:
    client.create_collection(collection_name=collection, vectors_config=models.VectorParams(size=16, distance=models.Distance.COSINE))

with open(model_path) as f:
    data = json.load(f)
vector = [random.random() for _ in range(16)]
payload = {
    'service': service,
    'model': data,
    'generated_at': date,
}
client.upsert(collection_name=collection, points=[models.PointStruct(id=os.urandom(8).hex(), vector=vector, payload=payload)])
PY

log INFO "Threat model generation and storage complete"