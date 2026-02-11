from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Prompt Cache Optimization", version="1.0.0")
requests_total = Counter("prompt_cache_optimization_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-149-prompt-cache-optimization", "system": 149}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-149-prompt-cache-optimization"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-149-prompt-cache-optimization",
        "name": "Prompt Cache Optimization",
        "system": 149,
        "port": int(os.getenv("SERVICE_PORT", "10149")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
