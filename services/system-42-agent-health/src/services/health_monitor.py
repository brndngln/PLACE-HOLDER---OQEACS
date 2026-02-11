"""
System 42 — Agent Health Monitor (orchestrator).

Ties together poison-pill tests, golden tests, and drift detection
into a single coherent health picture per agent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from src.models import (
    AgentHealthSummary,
    BenchmarkResult,
)
from src.services.drift_detector import DriftDetector
from src.services.golden_tests import GoldenTestRunner
from src.services.poison_pills import PoisonPillRunner

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Default list of known agents.  In production this would come from a
# service registry or database; here we keep a sensible static list.
DEFAULT_AGENTS: list[str] = [
    "gpt-4o",
    "gpt-4o-mini",
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "deepseek-coder",
]


class AgentHealthMonitor:
    """Facade that orchestrates all health-check sub-systems."""

    def __init__(self, db_pool: Any | None = None) -> None:
        self.poison_runner = PoisonPillRunner()
        self.golden_runner = GoldenTestRunner()
        self.drift_detector = DriftDetector(db_pool=db_pool)
        self._db_pool = db_pool

    # ── public API ──────────────────────────────────────────────────

    async def list_agents(self) -> list[str]:
        """Return the list of agents known to the monitor."""
        if self._db_pool is not None:
            try:
                async with self._db_pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT DISTINCT agent_id FROM agent_performance_history "
                        "ORDER BY agent_id"
                    )
                    if rows:
                        return [row["agent_id"] for row in rows]
            except Exception as exc:
                logger.warning("list_agents_db_fallback", error=str(exc))
        return list(DEFAULT_AGENTS)

    async def get_agent_health(self, agent_id: str) -> AgentHealthSummary:
        """Compute the current health summary for a single agent by
        aggregating cached results from each sub-system."""
        # Poison pill pass rate
        pp_results = self.poison_runner.get_results(agent_id)
        if pp_results:
            pp_pass_rate = sum(1 for r in pp_results if r.passed) / len(pp_results)
        else:
            pp_pass_rate = 0.0

        # Golden test pass rate
        gt_results = self.golden_runner.get_results(agent_id)
        if gt_results:
            gt_pass_rate = sum(1 for r in gt_results if r.passed) / len(gt_results)
        else:
            gt_pass_rate = 0.0

        # Drift status
        drift_report = await self.drift_detector.detect_drift(agent_id, days=30)
        if drift_report.drift_percentage < -10.0:
            drift_status = "degrading"
        elif drift_report.drift_percentage > 5.0:
            drift_status = "improving"
        elif drift_report.history:
            drift_status = "stable"
        else:
            drift_status = "unknown"

        # Overall score: weighted average
        overall = round(
            pp_pass_rate * 0.4 + gt_pass_rate * 0.4 + (1.0 if drift_status in ("stable", "improving") else 0.0) * 0.2,
            4,
        )

        return AgentHealthSummary(
            agent_id=agent_id,
            overall_score=overall,
            poison_pill_pass_rate=round(pp_pass_rate, 4),
            golden_test_pass_rate=round(gt_pass_rate, 4),
            drift_status=drift_status,
            last_check=datetime.now(timezone.utc),
        )

    async def run_full_benchmark(self, agent_id: str) -> BenchmarkResult:
        """Run all sub-systems against *agent_id* and return a
        consolidated benchmark result."""
        logger.info("benchmark_start", agent_id=agent_id)

        pp_report = await self.poison_runner.run_suite(agent_id)
        gt_results = await self.golden_runner.run_suite(agent_id)
        drift_report = await self.drift_detector.detect_drift(agent_id)

        pp_score = pp_report.passed / pp_report.total if pp_report.total else 0.0
        gt_score = (
            sum(r.score for r in gt_results) / len(gt_results)
            if gt_results
            else 0.0
        )
        drift_score = max(0.0, min(1.0, 1.0 + drift_report.drift_percentage / 100.0))

        scores = {
            "security": round(pp_score, 4),
            "quality": round(gt_score, 4),
            "stability": round(drift_score, 4),
        }
        overall = round(sum(scores.values()) / len(scores), 4)

        result = BenchmarkResult(
            agent_id=agent_id,
            scores=scores,
            overall=overall,
        )

        logger.info(
            "benchmark_complete",
            agent_id=agent_id,
            overall=overall,
            scores=scores,
        )
        return result
