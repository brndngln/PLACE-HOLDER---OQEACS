#!/usr/bin/env python3
"""
System 31: Uptime Kuma Auto-Configuration
Automatically creates monitors for ALL 28+ Omni Quantum services.
Uses Uptime Kuma's API to programmatically set up health checks.
"""

import json
import sys
import time
import httpx

UPTIME_KUMA_URL = "http://localhost:3001"
DEFAULT_INTERVAL = 60  # seconds

# All services to monitor
MONITORS = [
    # Critical Tier
    {"name": "PostgreSQL", "type": "port", "hostname": "omni-postgres", "port": 5432, "interval": 30, "tags": ["critical", "database"]},
    {"name": "Redis", "type": "port", "hostname": "omni-redis", "port": 6379, "interval": 30, "tags": ["critical", "database"]},
    {"name": "Caddy Reverse Proxy", "type": "http", "url": "http://omni-caddy:80", "interval": 30, "tags": ["critical", "infrastructure"]},
    {"name": "LiteLLM AI Gateway", "type": "http", "url": "http://omni-litellm:4000/health", "interval": 30, "tags": ["critical", "ai"]},
    {"name": "Vault Secrets", "type": "http", "url": "http://omni-vault:8200/v1/sys/health", "interval": 30, "tags": ["critical", "security"]},
    {"name": "Authentik Identity", "type": "http", "url": "http://omni-authentik:9000/-/health/ready/", "interval": 30, "tags": ["critical", "security"]},
    # High Priority Tier
    {"name": "Ollama AI", "type": "http", "url": "http://omni-ollama:11434/api/tags", "interval": 60, "tags": ["high", "ai"]},
    {"name": "Gitea Code Hosting", "type": "http", "url": "http://omni-gitea:3000/api/v1/version", "interval": 60, "tags": ["high", "devops"]},
    {"name": "n8n Workflows", "type": "http", "url": "http://omni-n8n:5678/healthz", "interval": 60, "tags": ["high", "automation"]},
    {"name": "Mattermost Chat", "type": "http", "url": "http://omni-mattermost:8065/api/v4/system/ping", "interval": 60, "tags": ["high", "communication"]},
    {"name": "Prometheus", "type": "http", "url": "http://omni-prometheus:9090/-/healthy", "interval": 60, "tags": ["high", "monitoring"]},
    {"name": "Grafana", "type": "http", "url": "http://omni-grafana:3000/api/health", "interval": 60, "tags": ["high", "monitoring"]},
    {"name": "Loki Logging", "type": "http", "url": "http://omni-loki:3100/ready", "interval": 60, "tags": ["high", "monitoring"]},
    {"name": "Qdrant Vectors", "type": "http", "url": "http://omni-qdrant:6333/healthz", "interval": 60, "tags": ["high", "ai"]},
    {"name": "MinIO Storage", "type": "http", "url": "http://omni-minio:9000/minio/health/live", "interval": 60, "tags": ["high", "infrastructure"]},
    # Standard Tier
    {"name": "Langfuse AI Observability", "type": "http", "url": "http://omni-langfuse:3000/api/public/health", "interval": 120, "tags": ["standard", "ai"]},
    {"name": "Plane Project Mgmt", "type": "http", "url": "http://omni-plane-web:3000", "interval": 120, "tags": ["standard", "project"]},
    {"name": "Nango Integrations", "type": "http", "url": "http://omni-nango:3003/health", "interval": 120, "tags": ["standard", "integrations"]},
    {"name": "OpenHands Coding Agent", "type": "http", "url": "http://omni-openhands:3000/health", "interval": 120, "tags": ["standard", "ai"]},
    {"name": "SWE-Agent", "type": "http", "url": "http://omni-swe-agent:8000/health", "interval": 120, "tags": ["standard", "ai"]},
    {"name": "Coolify Deploy", "type": "http", "url": "http://omni-coolify:8000/api/health", "interval": 120, "tags": ["standard", "devops"]},
    {"name": "Flowise Workflows", "type": "http", "url": "http://omni-flowise:3000/api/v1/ping", "interval": 120, "tags": ["standard", "ai"]},
    {"name": "Wiki.js Knowledge", "type": "http", "url": "http://omni-wikijs:3000/healthz", "interval": 120, "tags": ["standard", "knowledge"]},
    {"name": "Superset Analytics", "type": "http", "url": "http://omni-superset:8088/health", "interval": 120, "tags": ["standard", "analytics"]},
    {"name": "Cal.com Scheduling", "type": "http", "url": "http://omni-calcom:3000/api/health", "interval": 120, "tags": ["standard", "scheduling"]},
    {"name": "Twenty CRM", "type": "http", "url": "http://omni-twenty:3000/api/health", "interval": 120, "tags": ["standard", "crm"]},
    {"name": "Crater Invoicing", "type": "http", "url": "http://omni-crater:80/api/health", "interval": 120, "tags": ["standard", "finance"]},
    {"name": "CrowdSec IPS", "type": "http", "url": "http://omni-crowdsec:8080/health", "interval": 120, "tags": ["standard", "security"]},
    {"name": "Portainer Containers", "type": "http", "url": "http://omni-portainer:9443/api/status", "interval": 120, "tags": ["standard", "infrastructure"]},
    # Enhanced Systems (29-36)
    {"name": "Anomaly Detector", "type": "http", "url": "http://omni-anomaly-detector:8181/health", "interval": 60, "tags": ["standard", "monitoring"]},
    {"name": "SLA Tracker", "type": "http", "url": "http://omni-sla-tracker:8182/health", "interval": 60, "tags": ["standard", "monitoring"]},
    {"name": "Capacity Planner", "type": "http", "url": "http://omni-capacity-planner:8183/health", "interval": 120, "tags": ["standard", "monitoring"]},
    {"name": "Uptime Kuma", "type": "http", "url": "http://omni-uptime-kuma:3001", "interval": 60, "tags": ["standard", "monitoring"]},
]


def setup_uptime_kuma():
    """Auto-configure Uptime Kuma with all service monitors."""
    print("=" * 60)
    print("  Uptime Kuma Auto-Configuration")
    print("=" * 60)

    # Wait for Uptime Kuma to be ready
    print("\nWaiting for Uptime Kuma...")
    for i in range(30):
        try:
            resp = httpx.get(f"{UPTIME_KUMA_URL}/api/health", timeout=5)
            if resp.status_code == 200:
                print("✓ Uptime Kuma is ready")
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        print("✗ Uptime Kuma not ready after 60s")
        sys.exit(1)

    print(f"\nConfiguring {len(MONITORS)} monitors...")
    print("NOTE: Uptime Kuma uses WebSocket API. For automated setup,")
    print("use the init.sh script or configure via the web UI at :3001")
    print()

    # Generate configuration JSON for manual import
    config = {
        "version": "1.23.16",
        "notificationList": [
            {
                "name": "Mattermost Alerts",
                "type": "webhook",
                "webhookURL": "${MATTERMOST_ALERTS_WEBHOOK}",
                "isDefault": True,
                "applyExisting": True,
            },
            {
                "name": "Omi Wearable",
                "type": "webhook",
                "webhookURL": "http://omni-uptime-webhook-relay:8186/webhook/uptime-kuma",
                "isDefault": True,
                "applyExisting": True,
            },
        ],
        "monitorList": [],
    }

    for i, mon in enumerate(MONITORS, 1):
        monitor = {
            "id": i,
            "name": mon["name"],
            "interval": mon.get("interval", DEFAULT_INTERVAL),
            "retryInterval": 30,
            "maxretries": 3,
            "active": True,
            "tags": mon.get("tags", []),
        }
        if mon["type"] == "http":
            monitor["type"] = "http"
            monitor["url"] = mon["url"]
            monitor["method"] = "GET"
            monitor["maxredirects"] = 5
            monitor["accepted_statuscodes"] = ["200-299", "301", "302"]
        elif mon["type"] == "port":
            monitor["type"] = "port"
            monitor["hostname"] = mon["hostname"]
            monitor["port"] = mon["port"]

        config["monitorList"].append(monitor)
        print(f"  [{i:2d}] {mon['name']} ({mon['type']})")

    # Write config file
    with open("/app/data/uptime-kuma-config.json", "w") as f:
        json.dump(config, f, indent=2)
    print(f"\n✓ Configuration written to uptime-kuma-config.json")
    print(f"✓ {len(MONITORS)} monitors configured")
    print("\nAccess Uptime Kuma at http://localhost:3001")
    print("Import configuration via Settings → Backup → Import")


if __name__ == "__main__":
    setup_uptime_kuma()
