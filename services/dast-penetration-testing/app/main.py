from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="DAST Penetration Testing (ZAP)", version="1.0.0")
requests_total = Counter("dast-penetration-testing_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "dast-penetration-testing", "system": 67}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "dast-penetration-testing"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "dast-penetration-testing",
        "name": "DAST Penetration Testing (ZAP)",
        "system": 67,
        "port": int(os.getenv("SERVICE_PORT", "8090")),
        "version": "1.0.0",
    }


@app.get("/dast")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "dast",
        "service": "dast-penetration-testing",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
