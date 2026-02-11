from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Provenance and Signing", version="1.0.0")
requests_total = Counter("provenance_signing_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-80-provenance-signing", "system": 80}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-80-provenance-signing"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-80-provenance-signing",
        "name": "Provenance and Signing",
        "system": 80,
        "port": int(os.getenv("SERVICE_PORT", "10080")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
