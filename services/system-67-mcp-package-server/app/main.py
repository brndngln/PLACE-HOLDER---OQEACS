from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = FastAPI(title="MCP Package Server", version="1.0.0")
requests_total = Counter("mcp_package_server_requests_total", "Total requests")


@app.get("/health")
def health() -> dict:
    requests_total.inc()
    return {"status": "healthy", "service": "system-67-mcp-package-server", "system": 67}


@app.get("/ready")
def ready() -> dict:
    requests_total.inc()
    return {"status": "ready", "service": "system-67-mcp-package-server"}


@app.get("/info")
def info() -> dict:
    requests_total.inc()
    return {
        "service": "system-67-mcp-package-server",
        "name": "MCP Package Server",
        "system": 67,
        "port": int(os.getenv("SERVICE_PORT", "10067")),
        "version": "1.0.0",
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
