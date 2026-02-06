#!/usr/bin/env python3
"""
ADR search tool

Search Architectural Decision Records stored in Qdrant. The script
performs a simple keyword search against the ADR titles and contents
stored as payload in the "adrs" collection. It prints matching ADR
titles, created timestamps and a short snippet where the query appears.
Usage:
    adr-search.py <query>
Environment variables:
    QDRANT_HOST – host of Qdrant (default omni-qdrant)
    QDRANT_PORT – port of Qdrant (default 6333)
"""

from __future__ import annotations

import os
import sys
from typing import List

from qdrant_client import QdrantClient


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: adr-search.py <query>")
        sys.exit(1)
    query = sys.argv[1].lower()
    host = os.getenv("QDRANT_HOST", "omni-qdrant")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    client = QdrantClient(host=host, port=port)
    collection = "adrs"
    try:
        offset = None
        matches: List[str] = []
        while True:
            res, offset = client.scroll(collection_name=collection, offset=offset, limit=64)
            for point in res:
                payload = point.payload or {}
                title = str(payload.get("title", ""))
                content = str(payload.get("content", ""))
                if query in title.lower() or query in content.lower():
                    snippet = ""
                    idx = content.lower().find(query)
                    if idx != -1:
                        start = max(0, idx - 30)
                        end = min(len(content), idx + 30)
                        snippet = content[start:end].replace("\n", " ")
                    created_at = payload.get("created_at", "?")
                    matches.append(f"{title} (created {created_at}): …{snippet}…")
            if offset is None:
                break
        if not matches:
            print("No ADRs matched the query")
        else:
            for m in matches:
                print(m)
    except Exception as exc:  # noqa: B902
        print(f"Error searching ADRs: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()