"""
Omni Quantum Elite — Enhanced Logging SDK
Unified client for Loki, Log Pattern Detector, and Log Correlator.
"""

from datetime import datetime, timezone
from typing import Any

import httpx


class LoggingClient:
    """Unified client for System 30 Enhanced Logging."""

    def __init__(
        self,
        loki_url: str = "http://omni-loki:3100",
        pattern_detector_url: str = "http://omni-log-pattern-detector:8184",
        correlator_url: str = "http://omni-log-correlator:8185",
        timeout: float = 30.0,
    ):
        self.loki_url = loki_url
        self.pattern_detector_url = pattern_detector_url
        self.correlator_url = correlator_url
        self.timeout = timeout

    def query(self, logql: str, limit: int = 100) -> list[dict]:
        """Execute a LogQL query against Loki."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                f"{self.loki_url}/loki/api/v1/query_range",
                params={"query": logql, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            logs = []
            for stream in data.get("data", {}).get("result", []):
                for ts, line in stream.get("values", []):
                    logs.append({"timestamp": ts, "labels": stream.get("stream", {}), "line": line})
            return logs

    def get_service_logs(self, component: str, level: str | None = None, limit: int = 50) -> list[dict]:
        """Get logs for a specific service."""
        label_str = f'component="{component}"'
        if level:
            label_str += f', level="{level}"'
        return self.query(f"{{{label_str}}}", limit)

    def get_error_logs(self, component: str | None = None, limit: int = 100) -> list[dict]:
        """Get error/critical logs across services."""
        if component:
            return self.query(f'{{component="{component}", level=~"ERROR|CRITICAL"}}', limit)
        return self.query('{level=~"ERROR|CRITICAL"}', limit)

    def search_logs(self, text: str, component: str | None = None, limit: int = 50) -> list[dict]:
        """Full-text search across logs."""
        with httpx.Client(timeout=self.timeout) as client:
            params = {"text": text, "limit": limit}
            if component:
                params["component"] = component
            resp = client.get(f"{self.correlator_url}/search", params=params)
            resp.raise_for_status()
            return resp.json()

    def correlate_trace(self, trace_id: str) -> dict:
        """Correlate logs with Langfuse AI trace."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.correlator_url}/correlate/{trace_id}")
            resp.raise_for_status()
            return resp.json()

    def get_detected_patterns(self) -> dict:
        """Get current pattern detection status."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.pattern_detector_url}/patterns")
            resp.raise_for_status()
            return resp.json()

    def loki_ready(self) -> bool:
        """Check if Loki is ready."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.loki_url}/ready")
                return resp.status_code == 200
        except Exception:
            return False
