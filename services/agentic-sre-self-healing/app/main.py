from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Agentic SRE Self-Healing", version="1.0.0")
requests_total = Counter("agentic-sre-self-healing_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "agentic-sre-self-healing", "system": 58}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "agentic-sre-self-healing"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "agentic-sre-self-healing",
        "name": "Agentic SRE Self-Healing",
        "system": 58,
        "port": int(os.getenv("SERVICE_PORT", "9658")),
        "version": "1.0.0",
    }


@app.get("/self-heal")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "self-heal",
        "service": "agentic-sre-self-healing",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
