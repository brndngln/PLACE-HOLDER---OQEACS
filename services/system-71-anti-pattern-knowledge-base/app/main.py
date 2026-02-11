from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Anti-Pattern Knowledge Base", version="1.0.0")
requests_total = Counter("anti_pattern_knowledge_base_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-71-anti-pattern-knowledge-base", "system": 71}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-71-anti-pattern-knowledge-base"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-71-anti-pattern-knowledge-base",
        "name": "Anti-Pattern Knowledge Base",
        "system": 71,
        "port": int(os.getenv("SERVICE_PORT", "10071")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
