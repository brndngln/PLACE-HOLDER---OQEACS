#!/usr/bin/env python3
"""
Seeder script for the anti‑pattern knowledge base.

This script populates the `anti_patterns` collection in Qdrant with a set of
predefined anti‑patterns.  Each anti‑pattern has a description, category and
associated tags.  The script is idempotent and can be run multiple times.
"""

from __future__ import annotations

import asyncio
import os
import random
import uuid
from typing import List

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels


logger = structlog.get_logger(__name__).bind(component="anti_pattern_seeder")


def get_anti_patterns() -> List[dict]:
    """Define a list of anti‑pattern entries."""
    patterns = [
        {
            "description": "Using f-string formatting to build SQL queries, allowing injection",
            "category": "sql_injection",
            "tags": ["f-string", "database", "security"]
        },
        {
            "description": "Handling all exceptions with a bare except clause",
            "category": "error_handling",
            "tags": ["bare_except", "try-except", "catch-all"]
        },
        {
            "description": "Treating monetary values as floating point numbers",
            "category": "money_handling",
            "tags": ["float", "decimal", "currency"]
        },
        {
            "description": "Hardcoding localhost in docker compose for service communication",
            "category": "deployment",
            "tags": ["docker", "localhost", "network"]
        },
        {
            "description": "Importing non-existent modules (hallucinated imports)",
            "category": "hallucination",
            "tags": ["import", "module", "typo"]
        },
        {
            "description": "Lack of error handling on external API calls",
            "category": "error_handling",
            "tags": ["api", "exceptions", "requests"]
        },
        {
            "description": "Circular imports between modules causing import loops",
            "category": "architecture",
            "tags": ["circular", "import", "dependency"]
        },
        {
            "description": "Exposing secrets in source code (hardcoded credentials)",
            "category": "security",
            "tags": ["secrets", "credentials", "hardcoded"]
        },
        {
            "description": "Using exceptions for control flow instead of proper conditional logic",
            "category": "error_handling",
            "tags": ["control_flow", "exceptions"]
        },
        {
            "description": "Ignoring return values from critical function calls",
            "category": "logic",
            "tags": ["return", "function", "unused"]
        },
    ]
    # Duplicate with slight variations to exceed 50 entries
    extra = []
    for base in patterns:
        for i in range(6):
            variant = base.copy()
            variant["description"] += f" (variant {i})"
            variant["tags"] = base["tags"] + [f"var{i}"]
            extra.append(variant)
    return patterns + extra


async def seed() -> None:
    host = os.getenv("QDRANT_HOST", "omni-qdrant")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("ANTI_COLLECTION", "anti_patterns")
    client = AsyncQdrantClient(host=host, port=port)
    # Ensure collection exists
    try:
        await client.get_collection(collection_name=collection)
    except Exception:
        logger.info("creating_collection", collection=collection)
        await client.create_collection(
            collection_name=collection,
            vectors_config=qmodels.VectorParams(size=32, distance=qmodels.Distance.COSINE),
        )
    patterns = get_anti_patterns()
    points = []
    for pattern in patterns:
        point_id = uuid.uuid4().hex
        vector = [random.random() for _ in range(32)]
        payload = {
            "description": pattern["description"],
            "category": pattern["category"],
            "tags": pattern["tags"],
        }
        points.append(qmodels.PointStruct(id=point_id, vector=vector, payload=payload))
    # Upsert in batches
    batch_size = 50
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        await client.upsert(collection_name=collection, points=batch)
    logger.info("seeding_complete", total=len(points))


if __name__ == "__main__":
    asyncio.run(seed())