from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Code Completion (Tabby ML)", version="1.0.0")
requests_total = Counter("code-completion-tabby_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "code-completion-tabby", "system": 52}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "code-completion-tabby"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "code-completion-tabby",
        "name": "Code Completion (Tabby ML)",
        "system": 52,
        "port": int(os.getenv("SERVICE_PORT", "8320")),
        "version": "1.0.0",
    }


@app.get("/completions")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "completions",
        "service": "code-completion-tabby",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
