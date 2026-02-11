from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Sourcegraph Integration", version="1.0.0")
requests_total = Counter("sourcegraph_integration_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-62-sourcegraph-integration", "system": 62}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-62-sourcegraph-integration"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-62-sourcegraph-integration",
        "name": "Sourcegraph Integration",
        "system": 62,
        "port": int(os.getenv("SERVICE_PORT", "10062")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
