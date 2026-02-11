from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Embedding Pipeline Batch", version="1.0.0")
requests_total = Counter("embedding_pipeline_batch_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-95-embedding-pipeline-batch", "system": 95}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-95-embedding-pipeline-batch"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-95-embedding-pipeline-batch",
        "name": "Embedding Pipeline Batch",
        "system": 95,
        "port": int(os.getenv("SERVICE_PORT", "10095")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
