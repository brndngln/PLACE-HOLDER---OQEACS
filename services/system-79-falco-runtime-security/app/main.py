from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Falco Runtime Security", version="1.0.0")
requests_total = Counter("falco_runtime_security_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-79-falco-runtime-security", "system": 79}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-79-falco-runtime-security"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-79-falco-runtime-security",
        "name": "Falco Runtime Security",
        "system": 79,
        "port": int(os.getenv("SERVICE_PORT", "10079")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
