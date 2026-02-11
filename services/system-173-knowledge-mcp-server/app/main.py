from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Knowledge MCP Server", version="1.0.0")
requests_total = Counter("knowledge_mcp_server_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-173-knowledge-mcp-server", "system": 173}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-173-knowledge-mcp-server"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-173-knowledge-mcp-server",
        "name": "Knowledge MCP Server",
        "system": 173,
        "port": int(os.getenv("SERVICE_PORT", "10173")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
