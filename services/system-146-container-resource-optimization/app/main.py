from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Container Resource Optimization", version="1.0.0")
requests_total = Counter("container_resource_optimization_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-146-container-resource-optimization", "system": 146}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-146-container-resource-optimization"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-146-container-resource-optimization",
        "name": "Container Resource Optimization",
        "system": 146,
        "port": int(os.getenv("SERVICE_PORT", "10146")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
