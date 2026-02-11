from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Error Tracking GlitchTip", version="1.0.0")
requests_total = Counter("error_tracking_glitchtip_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-132-error-tracking-glitchtip", "system": 132}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-132-error-tracking-glitchtip"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-132-error-tracking-glitchtip",
        "name": "Error Tracking GlitchTip",
        "system": 132,
        "port": int(os.getenv("SERVICE_PORT", "10132")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
