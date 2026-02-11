from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Clean-Room Reproducibility", version="1.0.0")
requests_total = Counter("clean_room_reproducibility_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-64-clean-room-reproducibility", "system": 64}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-64-clean-room-reproducibility"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-64-clean-room-reproducibility",
        "name": "Clean-Room Reproducibility",
        "system": 64,
        "port": int(os.getenv("SERVICE_PORT", "10064")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
