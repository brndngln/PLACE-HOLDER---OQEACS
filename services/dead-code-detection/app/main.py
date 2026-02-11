from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Dead Code Detection", version="1.0.0")
requests_total = Counter("dead-code-detection_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "dead-code-detection", "system": 57}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "dead-code-detection"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "dead-code-detection",
        "name": "Dead Code Detection",
        "system": 57,
        "port": int(os.getenv("SERVICE_PORT", "9657")),
        "version": "1.0.0",
    }


@app.get("/dead-code")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "dead-code",
        "service": "dead-code-detection",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
