from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Translation Management Tolgee", version="1.0.0")
requests_total = Counter("translation_management_tolgee_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-139-translation-management-tolgee", "system": 139}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-139-translation-management-tolgee"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-139-translation-management-tolgee",
        "name": "Translation Management Tolgee",
        "system": 139,
        "port": int(os.getenv("SERVICE_PORT", "10139")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
