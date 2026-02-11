from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Webhooks Svix", version="1.0.0")
requests_total = Counter("webhooks_svix_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-136-webhooks-svix", "system": 136}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-136-webhooks-svix"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-136-webhooks-svix",
        "name": "Webhooks Svix",
        "system": 136,
        "port": int(os.getenv("SERVICE_PORT", "10136")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
