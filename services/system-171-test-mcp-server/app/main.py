from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="Test MCP Server", version="1.0.0")
requests_total = Counter("test_mcp_server_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-171-test-mcp-server", "system": 171}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-171-test-mcp-server"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-171-test-mcp-server",
        "name": "Test MCP Server",
        "system": 171,
        "port": int(os.getenv("SERVICE_PORT", "10171")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
