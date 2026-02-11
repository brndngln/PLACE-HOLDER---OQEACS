from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Architecture Diagram Generation", version="1.0.0")
requests_total = Counter("architecture-diagram-generation_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "architecture-diagram-generation", "system": 62}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "architecture-diagram-generation"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "architecture-diagram-generation",
        "name": "Architecture Diagram Generation",
        "system": 62,
        "port": int(os.getenv("SERVICE_PORT", "9662")),
        "version": "1.0.0",
    }


@app.get("/diagrams")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "diagrams",
        "service": "architecture-diagram-generation",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
