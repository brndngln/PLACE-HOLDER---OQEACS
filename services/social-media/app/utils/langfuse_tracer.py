from contextlib import asynccontextmanager
from datetime import datetime, timezone
import structlog
logger = structlog.get_logger()

@asynccontextmanager
async def traced_span(name: str, metadata: dict | None = None):
    logger.info('trace_start', span=name, metadata=metadata or {}, started_at=datetime.now(timezone.utc).isoformat())
    try:
        yield
    finally:
        logger.info('trace_end', span=name, finished_at=datetime.now(timezone.utc).isoformat())
