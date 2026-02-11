from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Dependency Existence Validation", version="1.0.0")
requests_total = Counter("dependency_existence_validation_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-60-dependency-existence-validation", "system": 60}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-60-dependency-existence-validation"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-60-dependency-existence-validation",
        "name": "Dependency Existence Validation",
        "system": 60,
        "port": int(os.getenv("SERVICE_PORT", "10060")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
