from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Pipeline Parallelization", version="1.0.0")
requests_total = Counter("pipeline_parallelization_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-141-pipeline-parallelization", "system": 141}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-141-pipeline-parallelization"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-141-pipeline-parallelization",
        "name": "Pipeline Parallelization",
        "system": 141,
        "port": int(os.getenv("SERVICE_PORT", "10141")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
