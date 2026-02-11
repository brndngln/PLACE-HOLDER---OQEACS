from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Spec-Driven Development", version="1.0.0")
requests_total = Counter("spec_driven_development_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-74-spec-driven-development", "system": 74}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-74-spec-driven-development"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-74-spec-driven-development",
        "name": "Spec-Driven Development",
        "system": 74,
        "port": int(os.getenv("SERVICE_PORT", "10074")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
