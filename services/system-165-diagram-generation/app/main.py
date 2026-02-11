from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Diagram Generation", version="1.0.0")
requests_total = Counter("diagram_generation_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-165-diagram-generation", "system": 165}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-165-diagram-generation"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-165-diagram-generation",
        "name": "Diagram Generation",
        "system": 165,
        "port": int(os.getenv("SERVICE_PORT", "10165")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
