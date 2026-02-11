from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Forms Formbricks", version="1.0.0")
requests_total = Counter("forms_formbricks_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-137-forms-formbricks", "system": 137}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-137-forms-formbricks"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-137-forms-formbricks",
        "name": "Forms Formbricks",
        "system": 137,
        "port": int(os.getenv("SERVICE_PORT", "10137")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
