from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Disaster Recovery Testing", version="1.0.0")
requests_total = Counter("disaster_recovery_testing_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-160-disaster-recovery-testing", "system": 160}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-160-disaster-recovery-testing"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-160-disaster-recovery-testing",
        "name": "Disaster Recovery Testing",
        "system": 160,
        "port": int(os.getenv("SERVICE_PORT", "10160")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
