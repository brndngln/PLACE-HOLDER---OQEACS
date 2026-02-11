from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Conference Talk Ingestor", version="1.0.0")
requests_total = Counter("conference_talk_ingestor_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-93-conference-talk-ingestor", "system": 93}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-93-conference-talk-ingestor"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-93-conference-talk-ingestor",
        "name": "Conference Talk Ingestor",
        "system": 93,
        "port": int(os.getenv("SERVICE_PORT", "10093")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
