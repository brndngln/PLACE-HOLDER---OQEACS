#!/usr/bin/env bash
#
# ADR creation tool
#
# This script generates a new Architectural Decision Record (ADR) from a
# template, commits it to a Git repository (Gitea) and indexes the
# document into Qdrant for searchability. It requires the following
# environment variables:
#   ADR_REPO          – Path to the local clone of the ADR Git repository
#   GITEA_REMOTE      – Remote URL for pushing changes (e.g. git@gitea.example.com:user/repo.git)
#   QDRANT_HOST       – Hostname of the Qdrant service (default omni-qdrant)
#   QDRANT_PORT       – Port of the Qdrant service (default 6333)

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <title>" >&2
  exit 1
fi

TITLE="$1"
ADR_REPO=${ADR_REPO:-adrs}
GITEA_REMOTE=${GITEA_REMOTE:-}
QDRANT_HOST=${QDRANT_HOST:-omni-qdrant}
QDRANT_PORT=${QDRANT_PORT:-6333}

mkdir -p "$ADR_REPO"

# Generate filename based on date and slug
slug=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-\|-$//g')
filename="$(date +%Y%m%d)-$slug.md"
filepath="$ADR_REPO/$filename"

# Populate template
template_path="$(dirname "$0")/../../templates/adr-template.md"
if [[ -f "$template_path" ]]; then
  sed "1s/<TITLE>/$TITLE/" "$template_path" >"$filepath"
else
  cat >"$filepath" <<EOF
# $TITLE

## Status

Proposed

## Context

## Decision

## Consequences

## Alternatives Considered
EOF
fi

echo "Created ADR file: $filepath"

# Commit and push if repository is a git repo and remote is defined
if [[ -d "$ADR_REPO/.git" ]]; then
  pushd "$ADR_REPO" >/dev/null
  git add "$filename"
  git commit -m "Add ADR: $TITLE" || true
  if [[ -n "$GITEA_REMOTE" ]]; then
    git push "$GITEA_REMOTE" HEAD || true
  fi
  popd >/dev/null
fi

# Index into Qdrant for searchability
python3 - <<PY
import json
import uuid
from datetime import datetime
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

adr_path = Path("$filepath")
with adr_path.open("r", encoding="utf-8") as fh:
    content = fh.read()

# Compute a simple embedding: length of content split into sections (10 dims)
parts = content.split('\n')
vector = [float(len(part) % 100) for part in parts[:10]]
vector += [0.0] * (10 - len(vector))

client = QdrantClient(host="$QDRANT_HOST", port=int("$QDRANT_PORT"))
collection = "adrs"
try:
    client.get_collection(collection)
except Exception:
    client.recreate_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=len(vector), distance=Distance.COSINE),
    )

point = PointStruct(
    id=str(uuid.uuid4()),
    vector=vector,
    payload={"title": "$TITLE", "content": content, "created_at": datetime.utcnow().isoformat()},
)
client.upsert(collection, [point])
print(f"Indexed ADR into Qdrant collection '{collection}'")
PY

echo "ADR created and indexed successfully"