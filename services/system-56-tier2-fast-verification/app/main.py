from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Tier 2 Fast Verification", version="1.0.0")
requests_total = Counter("tier2_fast_verification_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-56-tier2-fast-verification", "system": 56}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-56-tier2-fast-verification"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-56-tier2-fast-verification",
        "name": "Tier 2 Fast Verification",
        "system": 56,
        "port": int(os.getenv("SERVICE_PORT", "10056")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
