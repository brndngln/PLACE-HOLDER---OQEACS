from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Semantic Intent Verification", version="1.0.0")
requests_total = Counter("semantic_intent_verification_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-59-semantic-intent-verification", "system": 59}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-59-semantic-intent-verification"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-59-semantic-intent-verification",
        "name": "Semantic Intent Verification",
        "system": 59,
        "port": int(os.getenv("SERVICE_PORT", "10059")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
