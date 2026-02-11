from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="ADR Templates and Tracking", version="1.0.0")
requests_total = Counter("adr_templates_tracking_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-63-adr-templates-tracking", "system": 63}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-63-adr-templates-tracking"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-63-adr-templates-tracking",
        "name": "ADR Templates and Tracking",
        "system": 63,
        "port": int(os.getenv("SERVICE_PORT", "10063")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
