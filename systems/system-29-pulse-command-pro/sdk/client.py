"""
Omni Quantum Elite — Enhanced Monitoring SDK
Unified client for Prometheus, Thanos, Anomaly Detector, SLA Tracker, and Capacity Planner.
"""

import time
from datetime import datetime, timezone
from typing import Any

import httpx


class MonitoringClient:
    """Unified client for all System 29 monitoring components."""

    def __init__(
        self,
        prometheus_url: str = "http://omni-prometheus:9090",
        thanos_url: str = "http://omni-thanos-query:9091",
        grafana_url: str = "http://omni-grafana:3000",
        anomaly_url: str = "http://omni-anomaly-detector:8181",
        sla_url: str = "http://omni-sla-tracker:8182",
        capacity_url: str = "http://omni-capacity-planner:8183",
        karma_url: str = "http://omni-karma:8180",
        timeout: float = 30.0,
    ):
        self.prometheus_url = prometheus_url
        self.thanos_url = thanos_url
        self.grafana_url = grafana_url
        self.anomaly_url = anomaly_url
        self.sla_url = sla_url
        self.capacity_url = capacity_url
        self.karma_url = karma_url
        self.timeout = timeout

    # -----------------------------------------------------------------------
    # Prometheus / Thanos Queries
    # -----------------------------------------------------------------------
    def query(self, promql: str, use_thanos: bool = False) -> dict:
        """Execute an instant PromQL query."""
        url = self.thanos_url if use_thanos else self.prometheus_url
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{url}/api/v1/query", params={"query": promql})
            resp.raise_for_status()
            return resp.json()

    def query_range(
        self,
        promql: str,
        start: int | None = None,
        end: int | None = None,
        step: str = "60s",
        window: str = "1h",
        use_thanos: bool = False,
    ) -> dict:
        """Execute a range PromQL query."""
        url = self.thanos_url if use_thanos else self.prometheus_url
        if end is None:
            end = int(time.time())
        if start is None:
            duration_map = {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800, "30d": 2592000}
            start = end - duration_map.get(window, 3600)
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                f"{url}/api/v1/query_range",
                params={"query": promql, "start": start, "end": end, "step": step},
            )
            resp.raise_for_status()
            return resp.json()

    def get_targets(self) -> dict:
        """Get all Prometheus scrape targets and their status."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.prometheus_url}/api/v1/targets")
            resp.raise_for_status()
            return resp.json()

    def get_alerts(self) -> dict:
        """Get all active Prometheus alerts."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.prometheus_url}/api/v1/alerts")
            resp.raise_for_status()
            return resp.json()

    def get_rules(self) -> dict:
        """Get all Prometheus alert rules."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.prometheus_url}/api/v1/rules")
            resp.raise_for_status()
            return resp.json()

    # -----------------------------------------------------------------------
    # Service Health (quick checks)
    # -----------------------------------------------------------------------
    def service_up(self, job: str) -> bool:
        """Check if a specific service is up."""
        result = self.query(f'up{{job="{job}"}}')
        if result.get("data", {}).get("result"):
            return float(result["data"]["result"][0]["value"][1]) == 1
        return False

    def all_services_status(self) -> dict[str, bool]:
        """Get up/down status for all services."""
        result = self.query("up")
        status = {}
        for r in result.get("data", {}).get("result", []):
            job = r["metric"].get("job", "unknown")
            status[job] = float(r["value"][1]) == 1
        return status

    # -----------------------------------------------------------------------
    # Anomaly Detection
    # -----------------------------------------------------------------------
    def get_anomalies(self) -> dict:
        """Get currently active anomalies."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.anomaly_url}/anomalies")
            resp.raise_for_status()
            return resp.json()

    def trigger_anomaly_check(self) -> dict:
        """Trigger an on-demand anomaly check."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.anomaly_url}/check")
            resp.raise_for_status()
            return resp.json()

    def get_anomaly_config(self) -> dict:
        """Get anomaly detector configuration."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.anomaly_url}/config")
            resp.raise_for_status()
            return resp.json()

    # -----------------------------------------------------------------------
    # SLA Tracking
    # -----------------------------------------------------------------------
    def get_sla_status(self) -> dict:
        """Get current SLA status for all services."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.sla_url}/sla/status")
            resp.raise_for_status()
            return resp.json()

    def get_sla_report(self) -> dict:
        """Generate a full SLA compliance report."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.sla_url}/sla/report")
            resp.raise_for_status()
            return resp.json()

    # -----------------------------------------------------------------------
    # Capacity Planning
    # -----------------------------------------------------------------------
    def get_capacity_forecast(self) -> dict:
        """Get resource capacity forecasts."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.capacity_url}/forecast")
            resp.raise_for_status()
            return resp.json()

    # -----------------------------------------------------------------------
    # Grafana
    # -----------------------------------------------------------------------
    def grafana_health(self) -> dict:
        """Check Grafana health."""
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.grafana_url}/api/health")
            resp.raise_for_status()
            return resp.json()

    def list_dashboards(self, api_key: str = "") -> list[dict]:
        """List all Grafana dashboards."""
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.grafana_url}/api/search", headers=headers)
            resp.raise_for_status()
            return resp.json()

    # -----------------------------------------------------------------------
    # Unified Overview
    # -----------------------------------------------------------------------
    def platform_overview(self) -> dict:
        """Get a complete platform monitoring overview."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": self.all_services_status(),
            "active_alerts": len(self.get_alerts().get("data", {}).get("alerts", [])),
            "anomalies": self.get_anomalies(),
            "sla_report": self.get_sla_report(),
            "capacity": self.get_capacity_forecast(),
        }
