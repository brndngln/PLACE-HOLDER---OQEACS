from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

ORCH_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:9500")
TIMEOUT = 15.0

NEW_SERVICES: list[dict[str, Any]] = [
    # Prompt 1
    {"codename": "backup-fortress", "name": "Backup Fortress", "port": 9200, "tier": "high", "deps": ["omni-minio", "omni-postgres"], "system": 26, "group": "foundation", "deploy_group": 1},
    {"codename": "cryptographic-fortress", "name": "Cryptographic Fortress", "port": 8200, "tier": "critical", "deps": ["omni-postgres"], "system": 27, "group": "security", "deploy_group": 2},
    {"codename": "ai-gateway", "name": "AI Gateway", "port": 4000, "tier": "critical", "deps": ["omni-ollama", "omni-vault"], "system": 14, "group": "ai", "deploy_group": 6},
    {"codename": "observatory", "name": "Observatory", "port": 9090, "tier": "high", "deps": [], "system": 22, "group": "monitoring", "deploy_group": 3},
    {"codename": "code-fortress", "name": "Code Fortress", "port": 3000, "tier": "critical", "deps": ["omni-postgres"], "system": 12, "group": "core", "deploy_group": 3},
    {"codename": "object-store", "name": "Object Store", "port": 9000, "tier": "high", "deps": [], "system": 13, "group": "storage", "deploy_group": 1},
    {"codename": "gateway-sentinel", "name": "Gateway Sentinel", "port": 8080, "tier": "critical", "deps": ["omni-authentik"], "system": 18, "group": "security", "deploy_group": 4},
    # Prompt 2
    {"codename": "security-nexus", "name": "Security Nexus", "port": 9000, "tier": "critical", "deps": ["omni-vault"], "system": 19, "group": "security", "deploy_group": 4},
    {"codename": "security-shield", "name": "Security Shield", "port": 8088, "tier": "high", "deps": ["omni-gateway-sentinel"], "system": 20, "group": "security", "deploy_group": 4},
    {"codename": "cryptographic-fortress-pro", "name": "Cryptographic Fortress Pro", "port": 8210, "tier": "high", "deps": ["omni-vault"], "system": 21, "group": "security", "deploy_group": 4},
    # Prompt 3
    {"codename": "log-nexus", "name": "Log Nexus", "port": 3100, "tier": "high", "deps": [], "system": 23, "group": "monitoring", "deploy_group": 3},
    {"codename": "ai-observability", "name": "AI Observability", "port": 3000, "tier": "high", "deps": ["omni-postgres"], "system": 24, "group": "ai", "deploy_group": 6},
    {"codename": "container-manager", "name": "Container Manager", "port": 9000, "tier": "standard", "deps": [], "system": 25, "group": "dx", "deploy_group": 12},
    # Prompt 4
    {"codename": "communication-hub", "name": "Communication Hub", "port": 8065, "tier": "high", "deps": ["omni-postgres"], "system": 8, "group": "comms", "deploy_group": 5},
    {"codename": "webhook-router", "name": "Webhook Router", "port": 8066, "tier": "high", "deps": ["omni-mattermost"], "system": 9, "group": "comms", "deploy_group": 5},
    {"codename": "workflow-engine", "name": "Workflow Engine", "port": 5678, "tier": "high", "deps": ["omni-postgres"], "system": 10, "group": "comms", "deploy_group": 5},
    {"codename": "integration-hub", "name": "Integration Hub", "port": 3003, "tier": "high", "deps": ["omni-postgres"], "system": 11, "group": "comms", "deploy_group": 5},
    {"codename": "omi-bridge", "name": "Omi Bridge", "port": 9700, "tier": "standard", "deps": ["omni-webhook-router"], "system": 33, "group": "wearable", "deploy_group": 15},
    # Prompt 5
    {"codename": "neural-network", "name": "Neural Network", "port": 11434, "tier": "critical", "deps": [], "system": 15, "group": "ai", "deploy_group": 6},
    {"codename": "model-manager", "name": "Model Manager", "port": 11435, "tier": "high", "deps": ["omni-ollama"], "system": 34, "group": "ai", "deploy_group": 6},
    {"codename": "vector-memory", "name": "Vector Memory", "port": 6333, "tier": "critical", "deps": [], "system": 36, "group": "knowledge", "deploy_group": 3},
    {"codename": "snapshot-scheduler", "name": "Snapshot Scheduler", "port": 6334, "tier": "high", "deps": ["omni-qdrant"], "system": 43, "group": "knowledge", "deploy_group": 7},
    {"codename": "token-infinity-context", "name": "Token Infinity Context", "port": 9600, "tier": "critical", "deps": ["omni-qdrant", "omni-litellm"], "system": 16, "group": "ai", "deploy_group": 6},
    {"codename": "token-infinity-router", "name": "Token Infinity Router", "port": 9601, "tier": "critical", "deps": ["omni-token-infinity-context"], "system": 16, "group": "ai", "deploy_group": 6},
    {"codename": "ai-coder-alpha-orchestrator", "name": "AI Coder Alpha Orchestrator", "port": 9650, "tier": "high", "deps": ["omni-gitea", "omni-code-scorer"], "system": 16, "group": "pipeline", "deploy_group": 6},
    {"codename": "ai-coder-alpha-webhook", "name": "AI Coder Alpha Webhook", "port": 9651, "tier": "high", "deps": ["omni-ai-coder-alpha-orchestrator"], "system": 16, "group": "pipeline", "deploy_group": 6},
    {"codename": "ai-coder-beta-handler", "name": "AI Coder Beta Handler", "port": 9660, "tier": "high", "deps": ["omni-gitea", "omni-code-scorer"], "system": 17, "group": "pipeline", "deploy_group": 6},
    {"codename": "ai-coder-beta-intake", "name": "AI Coder Beta Intake", "port": 9661, "tier": "high", "deps": ["omni-ai-coder-beta-handler"], "system": 17, "group": "pipeline", "deploy_group": 6},
    {"codename": "build-forge", "name": "Build Forge", "port": 8000, "tier": "critical", "deps": ["omni-gitea"], "system": 35, "group": "pipeline", "deploy_group": 8},
    {"codename": "build-forge-notifier", "name": "Build Forge Notifier", "port": 8010, "tier": "high", "deps": ["omni-woodpecker-server"], "system": 35, "group": "pipeline", "deploy_group": 8},
    {"codename": "code-forge", "name": "Code Forge", "port": 7080, "tier": "high", "deps": ["omni-gitea"], "system": 44, "group": "pipeline", "deploy_group": 8},
    # Prompt 6
    {"codename": "knowledge-ingestor", "name": "Knowledge Ingestor", "port": 9420, "tier": "high", "deps": ["omni-qdrant", "omni-litellm", "omni-minio"], "system": 42, "group": "knowledge", "deploy_group": 7},
    {"codename": "knowledge-freshness", "name": "Knowledge Freshness", "port": 9430, "tier": "high", "deps": ["omni-knowledge-ingestor", "omni-qdrant"], "system": 43, "group": "knowledge", "deploy_group": 7},
    {"codename": "semantic-cache", "name": "Semantic Cache", "port": 9440, "tier": "high", "deps": ["omni-qdrant"], "system": 44, "group": "knowledge", "deploy_group": 7},
    {"codename": "neo4j-graphrag", "name": "Neo4j GraphRAG", "port": 7474, "tier": "high", "deps": ["omni-neo4j"], "system": 45, "group": "knowledge", "deploy_group": 3},
    {"codename": "pattern-query-api", "name": "Pattern Query API", "port": 9480, "tier": "standard", "deps": ["omni-neo4j"], "system": 45, "group": "knowledge", "deploy_group": 7},
    {"codename": "knowledge-base", "name": "Knowledge Base", "port": 3002, "tier": "standard", "deps": ["omni-postgres"], "system": 46, "group": "knowledge", "deploy_group": 7},
    # Prompt 7
    {"codename": "project-command", "name": "Project Command", "port": 3333, "tier": "high", "deps": ["omni-postgres"], "system": 47, "group": "business", "deploy_group": 9},
    {"codename": "project-command-sync", "name": "Project Command Sync", "port": 3334, "tier": "standard", "deps": ["omni-plane"], "system": 47, "group": "business", "deploy_group": 9},
    {"codename": "deploy-engine", "name": "Deploy Engine", "port": 8002, "tier": "high", "deps": ["omni-gitea"], "system": 48, "group": "business", "deploy_group": 9},
    {"codename": "flow-builder", "name": "Flow Builder", "port": 3001, "tier": "standard", "deps": ["omni-litellm"], "system": 49, "group": "business", "deploy_group": 9},
    {"codename": "analytics-engine", "name": "Analytics Engine", "port": 8088, "tier": "standard", "deps": ["omni-postgres"], "system": 50, "group": "business", "deploy_group": 9},
    {"codename": "schedule-manager", "name": "Schedule Manager", "port": 3005, "tier": "standard", "deps": ["omni-postgres"], "system": 51, "group": "business", "deploy_group": 9},
    {"codename": "crm-hub", "name": "CRM Hub", "port": 3006, "tier": "standard", "deps": ["omni-postgres"], "system": 52, "group": "business", "deploy_group": 9},
    {"codename": "crm-sync", "name": "CRM Sync", "port": 3007, "tier": "standard", "deps": ["omni-crm"], "system": 52, "group": "business", "deploy_group": 9},
    {"codename": "invoice-manager", "name": "Invoice Manager", "port": 3008, "tier": "standard", "deps": ["omni-postgres"], "system": 53, "group": "business", "deploy_group": 9},
    {"codename": "invoice-generator", "name": "Invoice Generator", "port": 3009, "tier": "standard", "deps": ["omni-invoice-manager"], "system": 53, "group": "business", "deploy_group": 9},
    # Prompt 8
    {"codename": "email-service", "name": "Email Service", "port": 9000, "tier": "standard", "deps": ["omni-postgres"], "system": 45, "group": "infra", "deploy_group": 10},
    {"codename": "support-center", "name": "Support Center", "port": 3011, "tier": "standard", "deps": ["omni-postgres"], "system": 47, "group": "infra", "deploy_group": 10},
    {"codename": "web-analytics", "name": "Web Analytics", "port": 8009, "tier": "standard", "deps": ["omni-postgres"], "system": 48, "group": "infra", "deploy_group": 10},
    {"codename": "feature-flags", "name": "Feature Flags", "port": 4242, "tier": "standard", "deps": ["omni-postgres"], "system": 50, "group": "infra", "deploy_group": 10},
    {"codename": "error-tracking", "name": "Error Tracking", "port": 8000, "tier": "standard", "deps": ["omni-postgres"], "system": 51, "group": "infra", "deploy_group": 10},
    {"codename": "search-engine", "name": "Search Engine", "port": 7700, "tier": "standard", "deps": ["omni-postgres"], "system": 52, "group": "infra", "deploy_group": 10},
    {"codename": "search-indexer", "name": "Search Indexer", "port": 7710, "tier": "standard", "deps": ["omni-search-engine"], "system": 52, "group": "infra", "deploy_group": 10},
    {"codename": "audit-logger", "name": "Audit Logger", "port": 9550, "tier": "high", "deps": ["omni-postgres"], "system": 55, "group": "infra", "deploy_group": 10},
    {"codename": "translation-mgmt", "name": "Translation Management", "port": 8081, "tier": "standard", "deps": ["omni-postgres"], "system": 58, "group": "infra", "deploy_group": 10},
    # Prompt 9
    {"codename": "api-gateway", "name": "API Gateway", "port": 8000, "tier": "high", "deps": ["omni-kong-postgres"], "system": 53, "group": "quality", "deploy_group": 11},
    {"codename": "contract-testing", "name": "Contract Testing", "port": 9292, "tier": "standard", "deps": ["omni-pact-postgres"], "system": 59, "group": "quality", "deploy_group": 11},
    {"codename": "contract-generator", "name": "Contract Generator", "port": 9293, "tier": "standard", "deps": ["omni-pact-broker"], "system": 59, "group": "quality", "deploy_group": 11},
    {"codename": "chaos-testing", "name": "Chaos Testing", "port": 8474, "tier": "standard", "deps": [], "system": 60, "group": "quality", "deploy_group": 11},
    {"codename": "ml-tracking", "name": "ML Tracking", "port": 5000, "tier": "standard", "deps": ["omni-mlflow-postgres", "omni-minio"], "system": 61, "group": "quality", "deploy_group": 11},
    {"codename": "experiment-tracker", "name": "Experiment Tracker", "port": 5001, "tier": "standard", "deps": ["omni-mlflow"], "system": 61, "group": "quality", "deploy_group": 11},
    {"codename": "benchmarking", "name": "Benchmarking", "port": 3000, "tier": "standard", "deps": [], "system": 63, "group": "quality", "deploy_group": 11},
    {"codename": "benchmark-runner", "name": "Benchmark Runner", "port": 3001, "tier": "standard", "deps": ["omni-bencher"], "system": 63, "group": "quality", "deploy_group": 11},
    # Prompt 10
    {"codename": "feedback-forms", "name": "Feedback Forms", "port": 3010, "tier": "standard", "deps": ["omni-formbricks-postgres", "omni-n8n"], "system": 56, "group": "dx", "deploy_group": 12},
    {"codename": "npm-registry", "name": "NPM Registry", "port": 4873, "tier": "standard", "deps": [], "system": 62, "group": "dx", "deploy_group": 12},
    {"codename": "db-admin", "name": "DB Admin", "port": 8978, "tier": "standard", "deps": ["omni-postgres"], "system": 64, "group": "dx", "deploy_group": 12},
]


def _guess_init_script(codename: str) -> str:
    candidates = [
        f"services/{codename}/scripts/init.sh",
        f"services/{codename}/scripts/{codename.split('-')[-1]}-init.sh",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return candidates[0]


def _guess_sdk_module(codename: str) -> str:
    candidates = [
        f"services/{codename}/sdk/client.py",
        f"services/{codename}/sdk/__init__.py",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return candidates[0]


def _default_urls(container: str, port: int) -> tuple[str, str, str]:
    health = f"http://{container}:{port}/health"
    ready = f"http://{container}:{port}/ready"
    metrics = f"http://{container}:{port}/metrics"
    if port in {3000, 3010}:
        health = f"http://{container}:{port}/api/health"
    if container == "omni-kong":
        health, ready, metrics = (
            "http://omni-kong:8100/status",
            "http://omni-kong:8100/status/ready",
            "http://omni-kong:8100/metrics",
        )
    if container == "omni-pact-broker":
        health = "http://omni-pact-broker:9292/diagnostic/status/heartbeat"
    if container == "omni-verdaccio":
        health = "http://omni-verdaccio:4873/-/ping"
    if container == "omni-cloudbeaver":
        health = "http://omni-cloudbeaver:8978/status"
    if container == "omni-toxiproxy":
        health = "http://omni-toxiproxy:8474/version"
    return health, ready, metrics


def to_registry_entry(raw: dict[str, Any]) -> dict[str, Any]:
    codename = raw["codename"]
    container = f"omni-{codename}"
    port = int(raw["port"])
    health_url, ready_url, metrics_url = _default_urls(container, port)

    return {
        "name": raw["name"],
        "codename": codename,
        "container": container,
        "port": port,
        "health_url": health_url,
        "ready_url": ready_url,
        "metrics_url": metrics_url,
        "tier": raw["tier"],
        "critical": raw["tier"] == "critical",
        "dependencies": raw.get("deps", []),
        "init_script": _guess_init_script(codename),
        "sdk_module": _guess_sdk_module(codename),
        "mattermost_channel": f"#{raw['group']}",
        "system_number": raw["system"],
        "group": raw["group"],
        "deploy_group": raw["deploy_group"],
    }


def load_existing() -> list[dict[str, Any]]:
    try:
        resp = httpx.get(f"{ORCH_URL}/api/services", timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "services" in data:
            return data["services"]
        if isinstance(data, list):
            return data
    except Exception:
        pass

    local_fallback = Path("services/master-orchestrator/config/service-registry.json")
    if local_fallback.exists():
        loaded = json.loads(local_fallback.read_text())
        if isinstance(loaded, dict):
            return loaded.get("services", [])
        return loaded
    return []


def save_local(services: list[dict[str, Any]]) -> None:
    out = Path("services/master-orchestrator/config/service-registry.generated.json")
    out.write_text(json.dumps({"services": services}, indent=2))


def push_registry(services: list[dict[str, Any]]) -> None:
    try:
        resp = httpx.put(f"{ORCH_URL}/api/services/registry", json={"services": services}, timeout=TIMEOUT)
        if resp.status_code >= 300:
            raise RuntimeError(resp.text)
    except Exception:
        for svc in services:
            try:
                httpx.post(f"{ORCH_URL}/api/services/register", json=svc, timeout=TIMEOUT)
            except Exception:
                continue


def main() -> None:
    existing = load_existing()
    merged = {s.get("codename", s.get("container", "")): s for s in existing if isinstance(s, dict)}

    for raw in NEW_SERVICES:
        merged[raw["codename"]] = to_registry_entry(raw)

    merged_services = sorted(merged.values(), key=lambda x: (x.get("deploy_group", 99), x.get("codename", "")))
    push_registry(merged_services)
    save_local(merged_services)

    print(f"Registry updated with {len(merged_services)} services")
    print("Run verification: curl http://localhost:9500/api/services | python -m json.tool | grep -c \"name\"")
    if len(merged_services) < 77:
        print("Warning: less than 77 services currently available; ensure base systems are loaded before rerun.")


if __name__ == "__main__":
    main()
