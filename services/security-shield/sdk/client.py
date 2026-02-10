#!/usr/bin/env python3
"""
SYSTEM 25 — SECURITY SHIELD: CrowdSec SDK Client
Omni Quantum Elite AI Coding System — Security & Identity Layer

Python client for the CrowdSec Local API (LAPI). Provides methods for
decision management, alert querying, metrics, and bouncer administration.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


class CrowdSecError(Exception):
    """Raised when a CrowdSec API call fails."""

    def __init__(self, message: str, status_code: int | None = None, detail: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class CrowdSecClient:
    """Client for the CrowdSec Local API (LAPI).

    Args:
        base_url: CrowdSec LAPI URL (e.g. http://omni-crowdsec:8080).
        api_key: Bouncer or machine API key.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-Api-Key": api_key,
                "Content-Type": "application/json",
                "User-Agent": "omni-quantum-sdk/1.0",
            },
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ───────────────────────────────────────────────────────────────
    # Internal
    # ───────────────────────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs) -> Any:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            raise CrowdSecError(
                f"CrowdSec API error: {method} {path} => {resp.status_code}",
                status_code=resp.status_code,
                detail=resp.text[:500],
            )
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # ───────────────────────────────────────────────────────────────
    # Decisions
    # ───────────────────────────────────────────────────────────────

    def get_decisions(
        self,
        ip: str | None = None,
        scope: str | None = None,
        scenario: str | None = None,
        decision_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get active decisions (bans, captchas, throttles).

        Args:
            ip: Filter by specific IP address.
            scope: Filter by scope (ip, range, etc.).
            scenario: Filter by scenario name.
            decision_type: Filter by type (ban, captcha, throttle).

        Returns:
            List of active decision objects.
        """
        params: dict[str, str] = {}
        if ip:
            params["ip"] = ip
        if scope:
            params["scope"] = scope
        if scenario:
            params["scenario"] = scenario
        if decision_type:
            params["type"] = decision_type

        result = self._request("GET", "/v1/decisions", params=params)
        return result if isinstance(result, list) else []

    def ban_ip(
        self,
        ip: str,
        duration: str = "4h",
        reason: str = "Manual ban via SDK",
        scenario: str = "omni-quantum/manual-ban",
    ) -> dict[str, Any] | None:
        """Ban an IP address.

        Args:
            ip: IP address to ban.
            duration: Ban duration (e.g. "4h", "24h", "7d").
            reason: Reason for the ban.
            scenario: Scenario name to associate.

        Returns:
            Decision ID if successful.
        """
        now = datetime.now(timezone.utc)
        payload = [
            {
                "scenario": scenario,
                "scenario_hash": "",
                "scenario_version": "",
                "simulated": False,
                "source": {
                    "scope": "ip",
                    "value": ip,
                },
                "start_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stop_at": "",
                "capacity": 0,
                "events_count": 1,
                "leakspeed": "",
                "message": reason,
                "decisions": [
                    {
                        "duration": duration,
                        "origin": "omni-quantum-sdk",
                        "scenario": scenario,
                        "scope": "ip",
                        "simulated": False,
                        "type": "ban",
                        "value": ip,
                    }
                ],
            }
        ]
        return self._request("POST", "/v1/alerts", json=payload)

    def unban_ip(self, ip: str) -> bool:
        """Remove all active decisions for an IP address.

        Args:
            ip: IP address to unban.

        Returns:
            True if decisions were deleted.
        """
        result = self._request("DELETE", "/v1/decisions", params={"ip": ip})
        return result is not None or True

    def check_ip(self, ip: str) -> dict[str, Any]:
        """Check if an IP has any active decisions.

        Returns:
            Dict with 'banned' bool and decision details if any.
        """
        decisions = self.get_decisions(ip=ip)
        return {
            "ip": ip,
            "banned": len(decisions) > 0,
            "decision_count": len(decisions),
            "decisions": decisions,
        }

    # ───────────────────────────────────────────────────────────────
    # Alerts
    # ───────────────────────────────────────────────────────────────

    def get_alerts(
        self,
        since: str = "24h",
        scenario: str | None = None,
        ip: str | None = None,
        has_active_decision: bool | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get alert history.

        Args:
            since: Lookback period (e.g. "24h", "7d", "30d").
            scenario: Filter by scenario.
            ip: Filter by source IP.
            has_active_decision: Filter by whether alert has active decision.
            limit: Maximum number of results.

        Returns:
            List of alert objects.
        """
        # Parse since string to datetime
        amount = int(since[:-1])
        unit = since[-1]
        if unit == "h":
            since_dt = datetime.now(timezone.utc) - timedelta(hours=amount)
        elif unit == "d":
            since_dt = datetime.now(timezone.utc) - timedelta(days=amount)
        else:
            since_dt = datetime.now(timezone.utc) - timedelta(hours=24)

        params: dict[str, Any] = {
            "since": since_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": limit,
        }
        if scenario:
            params["scenario"] = scenario
        if ip:
            params["ip"] = ip
        if has_active_decision is not None:
            params["has_active_decision"] = str(has_active_decision).lower()

        result = self._request("GET", "/v1/alerts", params=params)
        return result if isinstance(result, list) else []

    def get_alert_count(self, since: str = "24h") -> dict[str, int]:
        """Get count of alerts grouped by scenario.

        Returns:
            Dict mapping scenario names to alert counts.
        """
        alerts = self.get_alerts(since=since, limit=10000)
        counts: dict[str, int] = {}
        for alert in alerts:
            scenario = alert.get("scenario", "unknown")
            counts[scenario] = counts.get(scenario, 0) + 1
        return counts

    # ───────────────────────────────────────────────────────────────
    # Metrics
    # ───────────────────────────────────────────────────────────────

    def get_metrics(self) -> dict[str, Any]:
        """Get CrowdSec metrics (parsed from Prometheus endpoint).

        Returns:
            Dict with key metrics: total decisions, active bans,
            alerts per scenario, parser metrics.
        """
        try:
            resp = self._client.get(
                f"{self.base_url.replace(':8080', ':6060')}/metrics"
            )
            if resp.status_code != 200:
                return {"error": f"Metrics endpoint returned {resp.status_code}"}

            metrics: dict[str, Any] = {
                "raw_lines": 0,
                "active_decisions": 0,
                "total_alerts": 0,
                "scenarios": {},
                "parsers": {},
            }

            for line in resp.text.split("\n"):
                if line.startswith("#"):
                    continue
                if "cs_active_decisions" in line:
                    try:
                        metrics["active_decisions"] += int(float(line.split()[-1]))
                    except (ValueError, IndexError):
                        pass
                elif "cs_alerts_total" in line:
                    try:
                        metrics["total_alerts"] += int(float(line.split()[-1]))
                    except (ValueError, IndexError):
                        pass

            return metrics

        except Exception as e:
            return {"error": str(e)}

    # ───────────────────────────────────────────────────────────────
    # Bouncers
    # ───────────────────────────────────────────────────────────────

    def list_bouncers(self) -> list[dict[str, Any]]:
        """List all registered bouncers."""
        result = self._request("GET", "/v1/watchers")
        return result if isinstance(result, list) else []

    # ───────────────────────────────────────────────────────────────
    # Scenarios
    # ───────────────────────────────────────────────────────────────

    def list_scenarios(self) -> list[str]:
        """List all installed scenarios.

        Note: This queries the hub status rather than LAPI directly,
        so it returns scenario names from the installed collections.
        """
        alerts = self.get_alerts(since="720h", limit=10000)
        scenarios: set[str] = set()
        for alert in alerts:
            scenario = alert.get("scenario", "")
            if scenario:
                scenarios.add(scenario)
        return sorted(scenarios)

    # ───────────────────────────────────────────────────────────────
    # Health
    # ───────────────────────────────────────────────────────────────

    def health_check(self) -> dict[str, bool]:
        """Check CrowdSec LAPI health."""
        try:
            resp = self._client.get("/v1/heartbeat")
            return {"healthy": resp.status_code == 200}
        except Exception:
            return {"healthy": False}
