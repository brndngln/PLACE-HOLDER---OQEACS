from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Prompt Decay Detector", version="1.0.0")
requests_total = Counter("prompt_decay_detector_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-72-prompt-decay-detector", "system": 72}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-72-prompt-decay-detector"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-72-prompt-decay-detector",
        "name": "Prompt Decay Detector",
        "system": 72,
        "port": int(os.getenv("SERVICE_PORT", "10072")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
