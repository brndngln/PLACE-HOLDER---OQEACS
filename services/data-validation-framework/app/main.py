from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Data Validation Framework", version="1.0.0")
requests_total = Counter("data-validation-framework_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "data-validation-framework", "system": 68}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "data-validation-framework"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "data-validation-framework",
        "name": "Data Validation Framework",
        "system": 68,
        "port": int(os.getenv("SERVICE_PORT", "9668")),
        "version": "1.0.0",
    }


@app.get("/validate-data")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "validate-data",
        "service": "data-validation-framework",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
