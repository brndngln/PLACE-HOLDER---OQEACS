from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="SWE-bench Integration", version="1.0.0")
requests_total = Counter("swe_bench_integration_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-116-swe-bench-integration", "system": 116}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-116-swe-bench-integration"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-116-swe-bench-integration",
        "name": "SWE-bench Integration",
        "system": 116,
        "port": int(os.getenv("SERVICE_PORT", "10116")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
