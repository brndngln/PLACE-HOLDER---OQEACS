from __future__ import annotations

from datetime import datetime, timezone


def service_banner() -> dict[str, str]:
    return {
        "service": "retrospective-engine",
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
