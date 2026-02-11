from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Continuous Benchmarking", version="1.0.0")
requests_total = Counter("continuous_benchmarking_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-144-continuous-benchmarking", "system": 144}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-144-continuous-benchmarking"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-144-continuous-benchmarking",
        "name": "Continuous Benchmarking",
        "system": 144,
        "port": int(os.getenv("SERVICE_PORT", "10144")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
