from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Context Compiler", version="1.0.0")
requests_total = Counter("context_compiler_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-65-context-compiler", "system": 65}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-65-context-compiler"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-65-context-compiler",
        "name": "Context Compiler",
        "system": 65,
        "port": int(os.getenv("SERVICE_PORT", "10065")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
