from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="GraphRAG Pattern Library", version="1.0.0")
requests_total = Counter("graphrag_pattern_library_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-89-graphrag-pattern-library", "system": 89}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-89-graphrag-pattern-library"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-89-graphrag-pattern-library",
        "name": "GraphRAG Pattern Library",
        "system": 89,
        "port": int(os.getenv("SERVICE_PORT", "10089")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
