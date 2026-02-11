from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Build Caching Sccache", version="1.0.0")
requests_total = Counter("build_caching_sccache_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-147-build-caching-sccache", "system": 147}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-147-build-caching-sccache"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-147-build-caching-sccache",
        "name": "Build Caching Sccache",
        "system": 147,
        "port": int(os.getenv("SERVICE_PORT", "10147")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
