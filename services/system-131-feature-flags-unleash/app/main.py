from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Feature Flags Unleash", version="1.0.0")
requests_total = Counter("feature_flags_unleash_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-131-feature-flags-unleash", "system": 131}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-131-feature-flags-unleash"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-131-feature-flags-unleash",
        "name": "Feature Flags Unleash",
        "system": 131,
        "port": int(os.getenv("SERVICE_PORT", "10131")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
