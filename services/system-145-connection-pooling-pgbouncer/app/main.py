from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Connection Pooling PgBouncer", version="1.0.0")
requests_total = Counter("connection_pooling_pgbouncer_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-145-connection-pooling-pgbouncer", "system": 145}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-145-connection-pooling-pgbouncer"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-145-connection-pooling-pgbouncer",
        "name": "Connection Pooling PgBouncer",
        "system": 145,
        "port": int(os.getenv("SERVICE_PORT", "10145")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
