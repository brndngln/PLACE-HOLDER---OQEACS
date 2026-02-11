from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()


@asynccontextmanager
async def traced_span(name: str, metadata: dict | None = None):
    start = datetime.now(timezone.utc)
    logger.info("trace_start", span=name, metadata=metadata or {}, started_at=start.isoformat())
    try:
        yield
    finally:
        end = datetime.now(timezone.utc)
        logger.info("trace_end", span=name, finished_at=end.isoformat())
