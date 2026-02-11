from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="IaC Linting", version="1.0.0")
requests_total = Counter("iac_linting_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-77-iac-linting", "system": 77}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-77-iac-linting"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-77-iac-linting",
        "name": "IaC Linting",
        "system": 77,
        "port": int(os.getenv("SERVICE_PORT", "10077")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
