from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Domain Specific Intelligence", version="1.0.0")
requests_total = Counter("domain-specific-intelligence_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "domain-specific-intelligence", "system": 59}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "domain-specific-intelligence"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "domain-specific-intelligence",
        "name": "Domain Specific Intelligence",
        "system": 59,
        "port": int(os.getenv("SERVICE_PORT", "9659")),
        "version": "1.0.0",
    }


@app.get("/domains")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "domains",
        "service": "domain-specific-intelligence",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
