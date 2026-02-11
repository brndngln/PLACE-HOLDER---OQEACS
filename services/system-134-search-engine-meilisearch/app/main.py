from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Search Engine Meilisearch", version="1.0.0")
requests_total = Counter("search_engine_meilisearch_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-134-search-engine-meilisearch", "system": 134}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-134-search-engine-meilisearch"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-134-search-engine-meilisearch",
        "name": "Search Engine Meilisearch",
        "system": 134,
        "port": int(os.getenv("SERVICE_PORT", "10134")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
