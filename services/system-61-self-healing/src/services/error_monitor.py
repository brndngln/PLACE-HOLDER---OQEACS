from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from src.models import ErrorEvent


class ErrorMonitor:
    def __init__(self) -> None:
        self._seen: dict[str, ErrorEvent] = {}

    def poll_errors(self, source_events: list[dict] | None = None) -> list[ErrorEvent]:
        events = source_events or []
        fresh: list[ErrorEvent] = []
        for ev in events:
            sig = hashlib.sha1((ev.get("service", "") + ev.get("message", "")).encode()).hexdigest()
            if sig in self._seen:
                self._seen[sig].frequency += 1
                continue
            model = ErrorEvent(
                service=ev.get("service", "unknown"),
                error_type=ev.get("error_type", "runtime_error"),
                message=ev.get("message", ""),
                traceback=ev.get("traceback", ""),
                timestamp=ev.get("timestamp", datetime.now(timezone.utc).isoformat()),
                frequency=1,
            )
            self._seen[sig] = model
            fresh.append(model)
        return fresh
