from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Support Center Chatwoot", version="1.0.0")
requests_total = Counter("support_center_chatwoot_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-129-support-center-chatwoot", "system": 129}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-129-support-center-chatwoot"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-129-support-center-chatwoot",
        "name": "Support Center Chatwoot",
        "system": 129,
        "port": int(os.getenv("SERVICE_PORT", "10129")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
