"""
Tests for the DriftDetector calculation logic.

All tests use mock data — no database or network access required.
"""

from __future__ import annotations

import pytest

from src.services.drift_detector import DriftDetector


class TestCalculateDrift:
    """Unit tests for ``DriftDetector.calculate_drift``."""

    def test_stable_scores_return_zero(self) -> None:
        """Constant scores should yield 0 % drift."""
        scores = [0.85] * 30
        drift = DriftDetector.calculate_drift(scores, window=7)
        assert drift == 0.0

    def test_declining_scores_return_negative(self) -> None:
        """A clear downward trend should produce a negative drift
        percentage."""
        # 14 days: first 7 at 0.9, last 7 at 0.7
        scores = [0.9] * 7 + [0.7] * 7
        drift = DriftDetector.calculate_drift(scores, window=7)
        assert drift < 0.0
        # ~-22 %
        assert drift == pytest.approx(-22.22, abs=1.0)

    def test_improving_scores_return_positive(self) -> None:
        """An upward trend should produce a positive drift percentage."""
        scores = [0.6] * 7 + [0.9] * 7
        drift = DriftDetector.calculate_drift(scores, window=7)
        assert drift > 0.0
        # ~+50 %
        assert drift == pytest.approx(50.0, abs=1.0)

    def test_insufficient_data_returns_zero(self) -> None:
        """Fewer than 2 * window data points should return 0."""
        scores = [0.8] * 10  # < 14
        drift = DriftDetector.calculate_drift(scores, window=7)
        assert drift == 0.0

    def test_empty_list_returns_zero(self) -> None:
        drift = DriftDetector.calculate_drift([], window=7)
        assert drift == 0.0

    def test_single_value_returns_zero(self) -> None:
        drift = DriftDetector.calculate_drift([0.5], window=7)
        assert drift == 0.0

    def test_gradual_decline(self) -> None:
        """A slow, gradual decline over 30 days."""
        scores = [0.95 - (i * 0.01) for i in range(30)]
        drift = DriftDetector.calculate_drift(scores, window=7)
        # Should be negative — the rolling average drops
        assert drift < 0.0

    def test_noisy_but_stable(self) -> None:
        """Scores that oscillate around the same mean should be ~ 0 %
        drift."""
        import random

        random.seed(42)
        mean = 0.85
        scores = [mean + random.uniform(-0.05, 0.05) for _ in range(30)]
        drift = DriftDetector.calculate_drift(scores, window=7)
        # Should be close to zero (within +/- 5 %)
        assert abs(drift) < 5.0

    def test_baseline_zero_returns_zero(self) -> None:
        """When the baseline average is 0.0 we cannot divide, so drift
        must be 0."""
        scores = [0.0] * 7 + [0.5] * 7
        drift = DriftDetector.calculate_drift(scores, window=7)
        # Implementation guards against division by zero
        assert drift == 0.0

    def test_custom_window_size(self) -> None:
        """A smaller window should still produce a valid result."""
        scores = [0.9] * 3 + [0.7] * 3
        drift = DriftDetector.calculate_drift(scores, window=3)
        assert drift < 0.0


@pytest.mark.asyncio
async def test_detect_drift_without_db() -> None:
    """When no DB pool is provided, detect_drift should still return a
    valid (empty) DriftReport without raising."""
    detector = DriftDetector(db_pool=None)
    report = await detector.detect_drift("test-agent", days=30)
    assert report.agent_id == "test-agent"
    assert report.drift_percentage == 0.0
    assert report.history == []
