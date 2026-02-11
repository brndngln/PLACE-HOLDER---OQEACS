from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Email Service Listmonk", version="1.0.0")
requests_total = Counter("email_service_listmonk_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-128-email-service-listmonk", "system": 128}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-128-email-service-listmonk"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-128-email-service-listmonk",
        "name": "Email Service Listmonk",
        "system": 128,
        "port": int(os.getenv("SERVICE_PORT", "10128")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
