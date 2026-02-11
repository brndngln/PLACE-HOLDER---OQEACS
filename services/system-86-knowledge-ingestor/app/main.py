from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Knowledge Ingestor", version="1.0.0")
requests_total = Counter("knowledge_ingestor_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-86-knowledge-ingestor", "system": 86}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-86-knowledge-ingestor"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-86-knowledge-ingestor",
        "name": "Knowledge Ingestor",
        "system": 86,
        "port": int(os.getenv("SERVICE_PORT", "10086")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
