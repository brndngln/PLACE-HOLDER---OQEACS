from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

import httpx
import structlog
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)
CONTRACTS_TOTAL = Counter("contracts_generated_total", "Generated contracts", ["consumer", "provider"])
COVERAGE_GAUGE = Gauge("contracts_coverage_pairs", "Number of service pairs with contracts")

app = FastAPI(title="Contract Generator", version="1.1.0")

OPENAPI_MAP = {
    "omni-gitea": "http://omni-gitea:3000/swagger.v1.json",
    "omni-orchestrator": "http://omni-orchestrator:9500/openapi.json",
    "omni-knowledge-ingestor": "http://omni-knowledge-ingestor:9300/openapi.json",
    "omni-qdrant": "http://omni-qdrant:6333/openapi.json",
}


class ContractRequest(BaseModel):
    consumer: str
    provider: str


class ContractPair(BaseModel):
    consumer: str
    provider: str
    has_contract: bool


class GeneratorClient:
    def __init__(self) -> None:
        self.broker = os.getenv("PACT_BROKER_URL", "http://omni-pact-broker:9292")
        self.user = os.getenv("PACT_BROKER_USERNAME", "admin")
        self.password = os.getenv("PACT_BROKER_PASSWORD", "admin")
        self.audit_logger_url = os.getenv("AUDIT_LOGGER_URL", "http://omni-audit-logger:9550")
        self.client = httpx.Client(timeout=30.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        r = self.client.post(f"{self.broker}{path}", auth=(self.user, self.password), json=data)
        r.raise_for_status()
        return r.json() if r.text else {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def get(self, path: str) -> dict[str, Any]:
        r = self.client.get(f"{self.broker}{path}", auth=(self.user, self.password))
        r.raise_for_status()
        return r.json()

    def audit_event(self, event_type: str, details: dict[str, Any]) -> None:
        try:
            self.client.post(
                f"{self.audit_logger_url}/events",
                json={
                    "event_type": event_type,
                    "actor_type": "service",
                    "actor_id": "contract-generator",
                    "resource_type": "contract",
                    "resource_id": details.get("pair", "unknown"),
                    "action": "create",
                    "details": details,
                },
                timeout=5,
            )
        except Exception:
            logger.warning("audit_event_failed", event_type=event_type)


gen = GeneratorClient()


def generate_interactions_from_openapi(provider: str) -> list[dict[str, Any]]:
    url = OPENAPI_MAP.get(provider)
    if not url:
        return [{"description": f"fallback health check {provider}", "request": {"method": "GET", "path": "/health"}, "response": {"status": 200}}]

    resp = httpx.get(url, timeout=20.0)
    resp.raise_for_status()
    spec = resp.json()
    interactions: list[dict[str, Any]] = []
    for path, methods in list(spec.get("paths", {}).items())[:12]:
        if not isinstance(methods, dict):
            continue
        for m_name, op in methods.items():
            status = 200
            responses = op.get("responses", {}) if isinstance(op, dict) else {}
            if responses:
                numeric_status = [int(k) for k in responses.keys() if str(k).isdigit()]
                if numeric_status:
                    status = min(numeric_status)
            interactions.append(
                {
                    "description": op.get("summary", f"{m_name.upper()} {path}") if isinstance(op, dict) else f"{m_name.upper()} {path}",
                    "request": {"method": m_name.upper(), "path": path},
                    "response": {"status": status},
                }
            )
    return interactions or [{"description": f"fallback health check {provider}", "request": {"method": "GET", "path": "/health"}, "response": {"status": 200}}]


@app.post("/contracts/generate")
def generate_contract(req: ContractRequest) -> dict[str, Any]:
    interactions = generate_interactions_from_openapi(req.provider)
    contract = {
        "consumer": {"name": req.consumer},
        "provider": {"name": req.provider},
        "interactions": interactions,
    }
    version = os.getenv("CONTRACT_VERSION", "auto-generated")
    path = f"/pacts/provider/{req.provider}/consumer/{req.consumer}/version/{version}"
    gen.post(path, contract)
    CONTRACTS_TOTAL.labels(consumer=req.consumer, provider=req.provider).inc()
    gen.audit_event("contract_generated", {"pair": f"{req.consumer}->{req.provider}", "interactions": len(interactions)})
    return {"status": "published", "contract": contract}


@app.get("/contracts/coverage")
def coverage() -> dict[str, Any]:
    candidate_pairs = [
        ("omni-orchestrator", "omni-gitea"),
        ("omni-token-infinity", "omni-qdrant"),
        ("omni-openhands-orchestrator", "omni-gitea"),
        ("omni-knowledge-ingestor", "omni-qdrant"),
    ]
    pairs: list[ContractPair] = []
    covered = 0
    for c, p in candidate_pairs:
        try:
            gen.get(f"/pacts/provider/{p}/consumer/{c}/latest")
            has = True
        except Exception:
            has = False
        covered += 1 if has else 0
        pairs.append(ContractPair(consumer=c, provider=p, has_contract=has))

    COVERAGE_GAUGE.set(float(covered))
    return {"pairs": [m.model_dump() for m in pairs], "coverage_ratio": covered / max(len(candidate_pairs), 1)}


@app.post("/contracts/verify-all")
def verify_all() -> dict[str, Any]:
    # Trigger downstream CI workflow webhook
    payload = {
        "service": "contract-generator",
        "event": "verify-all",
        "target": "woodpecker-contract-verify",
    }
    try:
        httpx.post("http://omni-n8n:5678/webhook/contract-verify-all", json=payload, timeout=10)
    except Exception:
        logger.warning("verify_all_webhook_failed")
    return {"status": "triggered"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
