from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Distributed Tracing (Jaeger)", version="1.0.0")
requests_total = Counter("distributed-tracing-jaeger_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "distributed-tracing-jaeger", "system": 64}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "distributed-tracing-jaeger"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "distributed-tracing-jaeger",
        "name": "Distributed Tracing (Jaeger)",
        "system": 64,
        "port": int(os.getenv("SERVICE_PORT", "16686")),
        "version": "1.0.0",
    }


@app.get("/traces")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "traces",
        "service": "distributed-tracing-jaeger",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
