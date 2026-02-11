from datetime import datetime, timezone
import os

from fastapi import FastAPI

SYSTEM_ID = "135"
SYSTEM_SLUG = "event-bus"
SYSTEM_PORT = int(os.getenv("SYSTEM_PORT", "4222"))

app = FastAPI(
    title=f"Omni Quantum Elite - {SYSTEM_SLUG}",
    version="1.0.0",
    description=f"Deployable service for System {SYSTEM_ID}: {SYSTEM_SLUG}",
)


@app.get("/")
def root() -> dict:
    return {
        "system_id": SYSTEM_ID,
        "service": SYSTEM_SLUG,
        "port": SYSTEM_PORT,
        "status": "online",
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "service": SYSTEM_SLUG,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready() -> dict:
    return {
        "ready": True,
        "service": SYSTEM_SLUG,
    }
