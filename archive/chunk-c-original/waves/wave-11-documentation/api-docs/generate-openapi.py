#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════════════╗
# ║  API DOCUMENTATION GENERATOR — OpenAPI 3.1 Aggregation from All Services           ║
# ║  OMNI QUANTUM ELITE v3.0                                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════════════╝

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import yaml
import structlog

logger = structlog.get_logger()

# All FastAPI services with OpenAPI endpoints
SERVICES = [
    {"name": "orchestrator", "url": "http://omni-orchestrator:9500", "prefix": "/orchestrator"},
    {"name": "token-infinity", "url": "http://omni-token-infinity:9600", "prefix": "/token-infinity"},
    {"name": "omi-bridge", "url": "http://omni-omi-bridge:9700", "prefix": "/omi"},
    {"name": "semantic-cache", "url": "http://omni-semantic-cache:8380", "prefix": "/cache"},
    {"name": "cost-tracking", "url": "http://omni-cost-tracking:9622", "prefix": "/costs"},
    {"name": "blue-green", "url": "http://omni-blue-green:9650", "prefix": "/deploy/blue-green"},
    {"name": "canary", "url": "http://omni-canary:9651", "prefix": "/deploy/canary"},
    {"name": "rollback", "url": "http://omni-rollback:9652", "prefix": "/deploy/rollback"},
    {"name": "health-aggregator", "url": "http://omni-health-aggregator:9653", "prefix": "/health"},
    {"name": "notifier", "url": "http://omni-notifier:9654", "prefix": "/notify"},
]

async def fetch_openapi(session: aiohttp.ClientSession, service: Dict) -> Optional[Dict]:
    """Fetch OpenAPI spec from a service."""
    try:
        async with session.get(f"{service['url']}/openapi.json", timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                spec = await resp.json()
                logger.info("fetched_openapi", service=service["name"], paths=len(spec.get("paths", {})))
                return spec
            else:
                logger.warning("openapi_fetch_failed", service=service["name"], status=resp.status)
                return None
    except Exception as e:
        logger.warning("openapi_fetch_error", service=service["name"], error=str(e))
        return None

def merge_specs(specs: List[Dict], services: List[Dict]) -> Dict:
    """Merge multiple OpenAPI specs into one."""
    merged = {
        "openapi": "3.1.0",
        "info": {
            "title": "Omni Quantum Elite API",
            "description": "Unified API documentation for the Omni Quantum Elite AI Coding System",
            "version": "3.0.0",
            "contact": {
                "name": "Omni Quantum Elite",
                "url": "https://github.com/omni-quantum"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "servers": [
            {"url": "http://localhost:8080", "description": "Local Development"},
            {"url": "https://api.omni-quantum.local", "description": "Production"}
        ],
        "tags": [],
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                },
                "apiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            }
        }
    }

    for spec, service in zip(specs, services):
        if not spec:
            continue

        # Add tag for this service
        service_name = service["name"]
        merged["tags"].append({
            "name": service_name,
            "description": spec.get("info", {}).get("description", f"{service_name} API")
        })

        # Merge paths with prefix
        prefix = service["prefix"]
        for path, operations in spec.get("paths", {}).items():
            new_path = f"{prefix}{path}"
            
            # Add service tag to all operations
            for method, operation in operations.items():
                if isinstance(operation, dict):
                    operation["tags"] = [service_name]
            
            merged["paths"][new_path] = operations

        # Merge schemas (with service prefix to avoid conflicts)
        for schema_name, schema in spec.get("components", {}).get("schemas", {}).items():
            prefixed_name = f"{service_name}_{schema_name}"
            merged["components"]["schemas"][prefixed_name] = schema

    return merged

async def generate_docs(output_dir: Path):
    """Generate aggregated API documentation."""
    output_dir.mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_openapi(session, svc) for svc in SERVICES]
        specs = await asyncio.gather(*tasks)

    merged = merge_specs(specs, SERVICES)

    # Write OpenAPI JSON
    openapi_json = output_dir / "openapi.json"
    with open(openapi_json, 'w') as f:
        json.dump(merged, f, indent=2)
    logger.info("openapi_json_written", path=str(openapi_json))

    # Write OpenAPI YAML
    openapi_yaml = output_dir / "openapi.yaml"
    with open(openapi_yaml, 'w') as f:
        yaml.dump(merged, f, default_flow_style=False, sort_keys=False)
    logger.info("openapi_yaml_written", path=str(openapi_yaml))

    # Generate summary
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "services_documented": len([s for s in specs if s]),
        "total_paths": len(merged["paths"]),
        "total_schemas": len(merged["components"]["schemas"]),
        "services": [
            {
                "name": svc["name"],
                "documented": specs[i] is not None,
                "paths": len(specs[i].get("paths", {})) if specs[i] else 0
            }
            for i, svc in enumerate(SERVICES)
        ]
    }

    summary_file = output_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print("API DOCUMENTATION GENERATED")
    print(f"{'='*60}")
    print(f"Services documented: {summary['services_documented']}/{len(SERVICES)}")
    print(f"Total API paths: {summary['total_paths']}")
    print(f"Total schemas: {summary['total_schemas']}")
    print(f"Output directory: {output_dir}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="API Documentation Generator")
    parser.add_argument("--output", default="docs/api", help="Output directory")
    args = parser.parse_args()

    asyncio.run(generate_docs(Path(args.output)))

if __name__ == "__main__":
    main()
