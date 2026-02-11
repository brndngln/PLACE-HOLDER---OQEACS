from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Cross-Project Learning", version="1.0.0")
requests_total = Counter("cross_project_learning_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-73-cross-project-learning", "system": 73}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-73-cross-project-learning"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-73-cross-project-learning",
        "name": "Cross-Project Learning",
        "system": 73,
        "port": int(os.getenv("SERVICE_PORT", "10073")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
