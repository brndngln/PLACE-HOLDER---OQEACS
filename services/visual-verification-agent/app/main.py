from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Visual Verification Agent", version="1.0.0")
requests_total = Counter("visual-verification-agent_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "visual-verification-agent", "system": 71}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "visual-verification-agent"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "visual-verification-agent",
        "name": "Visual Verification Agent",
        "system": 71,
        "port": int(os.getenv("SERVICE_PORT", "9671")),
        "version": "1.0.0",
    }


@app.get("/visual-verify")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "visual-verify",
        "service": "visual-verification-agent",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
