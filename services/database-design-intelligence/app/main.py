from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Database Design Intelligence", version="1.0.0")
requests_total = Counter("database-design-intelligence_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "database-design-intelligence", "system": 54}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "database-design-intelligence"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "database-design-intelligence",
        "name": "Database Design Intelligence",
        "system": 54,
        "port": int(os.getenv("SERVICE_PORT", "9654")),
        "version": "1.0.0",
    }


@app.get("/schema-check")
def capability() -> dict:
    requests_total.inc()
    return {
        "capability": "schema-check",
        "service": "database-design-intelligence",
        "status": "enabled",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
