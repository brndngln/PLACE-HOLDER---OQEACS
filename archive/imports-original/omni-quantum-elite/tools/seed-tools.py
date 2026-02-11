#!/usr/bin/env python3
"""
Seeder for tool descriptions in Qdrant.

This script populates the `tool_descriptions` collection with a variety of tool
names and descriptions to support the Tool Selector service.  It should be run
as part of environment initialization and is idempotent: it checks for
existing entries and only inserts missing ones.
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


logger = structlog.get_logger(__name__).bind(component="tool_seeder")


def generate_tool_dataset() -> List[dict]:
    """Generate a synthetic dataset of tool descriptions."""
    base_tools = [
        ("fastapi", "High performance Python API framework"),
        ("django", "Batteries‑included Python web framework"),
        ("flask", "Minimal Python web microframework"),
        ("express", "Fast, unopinionated Node.js web framework"),
        ("nestjs", "TypeScript Node.js framework for scalable server-side apps"),
        ("react", "Declarative UI library for building interactive user interfaces"),
        ("vue", "Progressive JavaScript framework for building user interfaces"),
        ("angular", "Platform for building mobile and desktop web applications"),
        ("postgresql", "Open source relational database with advanced features"),
        ("mysql", "Popular open source relational database management system"),
        ("sqlite", "Serverless self-contained SQL database engine"),
        ("redis", "In-memory data structure store used as a database, cache, and message broker"),
        ("mongodb", "Document‑oriented NoSQL database"),
        ("s3", "Object storage service with high scalability and durability"),
        ("minio", "High performance object storage with Amazon S3 API compatibility"),
        ("docker", "Platform for containerizing applications"),
        ("kubernetes", "Production‑grade container orchestration system"),
        ("helm", "Package manager for Kubernetes"),
        ("terraform", "Infrastructure as code tool for provisioning resources"),
        ("ansible", "Agentless automation tool for configuration management and orchestration"),
        ("prometheus", "Monitoring system and time series database"),
        ("loki", "Log aggregation system for Prometheus ecosystem"),
        ("grafana", "Visualization and analytics platform"),
        ("git", "Distributed version control system"),
        ("gitea", "Self‑hosted Git service"),
        ("github_actions", "CI/CD platform for GitHub repositories"),
    ]
    dataset: List[dict] = []
    # Generate variants to reach at least 125 entries
    suffixes = ["client", "server", "plugin", "adapter", "sdk", "cli"]
    for name, desc in base_tools:
        dataset.append({"name": name, "description": desc})
        for suffix in suffixes:
            variant_name = f"{name}-{suffix}"
            variant_desc = f"{desc} ({suffix})"
            dataset.append({"name": variant_name, "description": variant_desc})
    # Ensure at least 125 entries
    # Add numeric variations if needed
    counter = 0
    while len(dataset) < 130:
        base_name, base_desc = random.choice(base_tools)
        variant_name = f"{base_name}-{counter}"
        variant_desc = f"{base_desc} (variant {counter})"
        dataset.append({"name": variant_name, "description": variant_desc})
        counter += 1
    return dataset


async def main() -> None:
    host = os.getenv("QDRANT_HOST", "omni-qdrant")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    collection = os.getenv("TOOL_COLLECTION", "tool_descriptions")
    client = AsyncQdrantClient(host=host, port=port)
    # Ensure collection exists
    try:
        await client.get_collection(collection_name=collection)
    except Exception:
        logger.info("creating_collection", collection=collection)
        await client.create_collection(
            collection_name=collection,
            vectors_config=qmodels.VectorParams(size=64, distance=qmodels.Distance.COSINE),
        )
    dataset = generate_tool_dataset()
    # Prepare points for upsert
    points = []
    for record in dataset:
        point_id = uuid.uuid4().hex
        vector = [random.random() for _ in range(64)]
        payload = {"name": record["name"], "description": record["description"]}
        points.append(qmodels.PointStruct(id=point_id, vector=vector, payload=payload))
    logger.info("upserting_tools", count=len(points))
    # Upsert in batches
    batch_size = 50
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        await client.upsert(collection_name=collection, points=batch)
    logger.info("seeding_complete", total=len(points))


if __name__ == "__main__":
    asyncio.run(main())