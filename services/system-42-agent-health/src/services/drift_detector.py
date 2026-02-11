"""
System 42 — Performance Drift Detector.

Queries the PostgreSQL performance-history table, computes a 7-day
rolling average, and compares the most recent window against the
baseline (first 7-day window in the requested range).  If the decline
exceeds 10 % a Mattermost alert is fired.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import structlog

from src.models import DriftReport
from src.utils.notifications import send_mattermost_alert

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Threshold: alert when performance drops more than 10 %
DRIFT_THRESHOLD_PERCENT: float = -10.0


class DriftDetector:
    """Detect agent performance drift from historical data."""

    def __init__(self, db_pool: Any | None = None) -> None:
        self._db_pool = db_pool

    async def _fetch_history(
        self,
        agent_id: str,
        days: int,
    ) -> list[dict[str, Any]]:
        """Pull performance rows from PostgreSQL for the given agent
        within the last *days* days.

        Each row is expected to contain at least ``recorded_at`` (date)
        and ``score`` (float 0..1).
        """
        if self._db_pool is None:
            logger.warning("drift_detector_no_db", agent_id=agent_id)
            return []

        query = """
            SELECT recorded_at, score, metadata
            FROM   agent_performance_history
            WHERE  agent_id = $1
              AND  recorded_at >= NOW() - ($2 || ' days')::INTERVAL
            ORDER  BY recorded_at ASC
        """
        rows: list[dict[str, Any]] = []
        try:
            async with self._db_pool.acquire() as conn:
                records = await conn.fetch(query, agent_id, str(days))
                for rec in records:
                    rows.append(
                        {
                            "recorded_at": rec["recorded_at"].isoformat()
                            if isinstance(rec["recorded_at"], datetime)
                            else str(rec["recorded_at"]),
                            "score": float(rec["score"]),
                            "metadata": dict(rec["metadata"])
                            if rec.get("metadata")
                            else {},
                        }
                    )
        except Exception as exc:
            logger.error(
                "drift_history_query_failed",
                agent_id=agent_id,
                error=str(exc),
            )
        return rows

    @staticmethod
    def calculate_drift(
        scores: list[float],
        window: int = 7,
    ) -> float:
        """Return drift percentage comparing the latest *window*-day
        average against the first *window*-day average.

        A negative value means degradation; positive means improvement.
        Returns 0.0 when there is not enough data.
        """
        if len(scores) < window * 2:
            return 0.0

        arr = np.array(scores, dtype=np.float64)

        # Rolling average via convolution
        kernel = np.ones(window) / window
        rolling = np.convolve(arr, kernel, mode="valid")

        if len(rolling) < 2:
            return 0.0

        baseline = float(rolling[0])
        recent = float(rolling[-1])

        if baseline == 0.0:
            return 0.0

        drift_pct = ((recent - baseline) / abs(baseline)) * 100.0
        return round(drift_pct, 2)

    async def detect_drift(
        self,
        agent_id: str,
        days: int = 30,
    ) -> DriftReport:
        """Run drift detection for *agent_id* over the last *days* days."""
        history = await self._fetch_history(agent_id, days)
        scores = [entry["score"] for entry in history]
        drift_pct = self.calculate_drift(scores)

        report = DriftReport(
            agent_id=agent_id,
            history=history,
            drift_percentage=drift_pct,
        )

        if drift_pct < DRIFT_THRESHOLD_PERCENT:
            logger.warning(
                "drift_alert",
                agent_id=agent_id,
                drift_pct=drift_pct,
            )
            await send_mattermost_alert(
                title=f"Performance Drift Detected: {agent_id}",
                message=(
                    f"Agent `{agent_id}` shows a **{drift_pct:.1f}%** "
                    f"performance decline over the last {days} days.\n\n"
                    f"Threshold: {DRIFT_THRESHOLD_PERCENT}%"
                ),
                severity="high",
                fields={
                    "Agent": agent_id,
                    "Drift": f"{drift_pct:.1f}%",
                    "Window": f"{days} days",
                    "Data points": str(len(scores)),
                },
            )
        else:
            status = "improving" if drift_pct > 0 else "stable"
            logger.info(
                "drift_check_ok",
                agent_id=agent_id,
                drift_pct=drift_pct,
                status=status,
            )

        return report
