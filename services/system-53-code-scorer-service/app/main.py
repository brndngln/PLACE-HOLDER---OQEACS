from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Code Scorer Service", version="1.0.0")
requests_total = Counter("code_scorer_service_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-53-code-scorer-service", "system": 53}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-53-code-scorer-service"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-53-code-scorer-service",
        "name": "Code Scorer Service",
        "system": 53,
        "port": int(os.getenv("SERVICE_PORT", "10053")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
