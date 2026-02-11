from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Auto Documentation Generator", version="1.0.0")
requests_total = Counter("auto_documentation_generator_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-159-auto-documentation-generator", "system": 159}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-159-auto-documentation-generator"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-159-auto-documentation-generator",
        "name": "Auto Documentation Generator",
        "system": 159,
        "port": int(os.getenv("SERVICE_PORT", "10159")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
