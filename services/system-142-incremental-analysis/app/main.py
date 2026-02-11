from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Incremental Analysis", version="1.0.0")
requests_total = Counter("incremental_analysis_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-142-incremental-analysis", "system": 142}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-142-incremental-analysis"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-142-incremental-analysis",
        "name": "Incremental Analysis",
        "system": 142,
        "port": int(os.getenv("SERVICE_PORT", "10142")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
