from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="MCP DB Schema Server", version="1.0.0")
requests_total = Counter("mcp_db_schema_server_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-69-mcp-db-schema-server", "system": 69}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-69-mcp-db-schema-server"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-69-mcp-db-schema-server",
        "name": "MCP DB Schema Server",
        "system": 69,
        "port": int(os.getenv("SERVICE_PORT", "10069")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
