from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Quality Gate Engine", version="1.0.0")
requests_total = Counter("quality_gate_engine_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-54-quality-gate-engine", "system": 54}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-54-quality-gate-engine"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-54-quality-gate-engine",
        "name": "Quality Gate Engine",
        "system": 54,
        "port": int(os.getenv("SERVICE_PORT", "10054")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
