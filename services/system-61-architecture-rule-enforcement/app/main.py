from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Architecture Rule Enforcement", version="1.0.0")
requests_total = Counter("architecture_rule_enforcement_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-61-architecture-rule-enforcement", "system": 61}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-61-architecture-rule-enforcement"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-61-architecture-rule-enforcement",
        "name": "Architecture Rule Enforcement",
        "system": 61,
        "port": int(os.getenv("SERVICE_PORT", "10061")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
